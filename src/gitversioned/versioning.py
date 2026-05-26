"""
GitVersioned core module for resolving versions from Git state.

This module provides the primary logic for computing PEP 440 compliant version
strings. It evaluates multiple configured sources (such as tags, branches, files,
and functions) and applies appropriate templates based on the current build
environment and repository state.
"""

from __future__ import annotations

import datetime
import importlib
import math
import re
import sys
from pathlib import Path
from typing import Any, Literal, cast

from loguru import logger
from packaging.version import InvalidVersion, Version
from tstr import generate_template, render

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository

__all__ = [
    "generate_version_file",
    "resolve_and_generate_version",
    "resolve_version",
]


def _extract_versions(patterns: list[str], text: str) -> list[Version]:
    """Extracts a Version object from a regex match group dictionary or groups."""
    versions: list[Version] = []
    for pattern in patterns:
        for match in re.finditer(str(pattern), text):
            groups = match.groupdict()
            major = groups.get("major")
            minor = groups.get("minor")
            micro = groups.get("micro") or groups.get("patch") or groups.get("bug")

            if major is None or minor is None or micro is None:
                logger.warning(
                    f"Invalid version string found for pattern {pattern} and "
                    f"text {text} with groups {groups}"
                )
                continue

            versions.append(Version(f"{major}.{minor}.{micro}"))

    if not versions:
        raise ValueError(f"No version found for patterns {patterns} and text {text}")

    return versions


def _resolve_explicit(settings: Settings) -> Version:
    """Checks if a hardcoded version is provided in settings."""
    version_str = str(settings.version).strip().lower()
    logger.debug(f"Evaluating explicit version setting: '{version_str}'")
    if version_str in ("auto", "dynamic", "0.0.0", ""):
        raise ValueError("Explicit version is not set.")
    version = _extract_versions(settings.regex_version, version_str)[0]
    logger.info(f"Resolved explicit version: {version}")
    return version


def _resolve_file(settings: Settings) -> Version:
    """Resolves version from the configured version file."""
    if not settings.version_source_file:
        logger.debug("No version_source_file configured.")
        raise ValueError("No version_source_file configured.")

    file_path = Path(settings.version_source_file)
    target = file_path if file_path.is_absolute() else settings.src_root / file_path
    logger.debug(f"Attempting to resolve version from file: {target}")

    if not target.exists():
        logger.info(f"Version file not found: {target}")
        raise ValueError("Version file not found.")

    content = target.read_text(encoding="utf-8")
    version = _extract_versions(settings.regex_file, content)[0]
    logger.info(
        f"Resolved version from file '{target}' using pattern "
        f"{settings.regex_file}: {version}"
    )
    return version


def _resolve_function(
    settings: Settings, repo: GitRepository, env: BuildEnvironment
) -> tuple[Version, GitReference | None]:
    """Resolves version by executing a configured python function."""
    if not settings.version_source_function:
        logger.debug("No version_source_function configured.")
        raise ValueError("No version_source_function configured.")

    logger.debug(
        f"Attempting to resolve version from function: "
        f"{settings.version_source_function}"
    )

    # Insert into PATH to allow general importing within the package
    added_paths = []
    for path in [str(settings.project_root), str(settings.src_root)]:
        if path not in sys.path:
            sys.path.insert(0, path)
            added_paths.append(path)

    try:
        module_name, function_name = str(settings.version_source_function).split(":", 1)
        module = importlib.import_module(module_name)  # nosemgrep
        version, ref = getattr(module, function_name)(
            settings=settings, repo=repo, env=env
        )
        if not version or not isinstance(version, Version):
            raise ValueError(
                f"Version function '{settings.version_source_function}' did not "
                f"return a valid version. Got: {version}"
            )
        if ref and not isinstance(ref, GitReference):
            raise ValueError(
                f"Version function '{settings.version_source_function}' did not "
                f"return a valid reference. Got: {ref}"
            )
        logger.info(
            f"Resolved version and reference from function "
            f"{settings.version_source_function}: {version} ({ref})"
        )
        return version, ref
    except Exception as error:
        logger.exception(
            f"Version function '{settings.version_source_function}' failed: {error}"
        )
        raise
    finally:
        for path in added_paths:
            if path in sys.path:
                sys.path.remove(path)


def _resolve_git(
    type_: Literal["tag", "branch", "commit"],
    settings: Settings,
    repository: GitRepository,
) -> tuple[Version, GitReference | None]:
    """Generic logic for matching Git objects against regex patterns."""
    logger.debug(f"Attempting to resolve version from git {type_}")

    if not repository.is_available:
        logger.warning("No git repository available.")
        raise ValueError("No git repository available.")

    candidates: list[tuple[str, GitReference | None]] = []
    if type_ == "tag":
        patterns = settings.regex_tag
        candidates = [(tag.tag_name, tag) for tag in repository.tags]
    elif type_ == "branch":
        patterns = settings.regex_branch
        candidates = [
            (
                (
                    repository.current_branch.branch_name
                    if repository.current_branch
                    else ""
                ),
                repository.current_branch,
            )
        ]
    elif type_ == "commit":
        patterns = settings.regex_commit
        candidates = [(commit.commit_message, commit) for commit in repository.commits]
    else:
        raise ValueError(f"Invalid git type: {type_}")

    matches: list[tuple[Version, GitReference | None]] = []
    for text, reference in candidates:
        try:
            version = _extract_versions(patterns, text)[0]
            matches.append((version, reference))
        except (InvalidVersion, ValueError) as ver_err:
            logger.warning(
                f"Could not extract version from git {type_} '{text}' using "
                f"patterns {patterns}: {ver_err}"
            )
            continue

    if not matches:
        raise ValueError(f"No version found for git {type_} using patterns {patterns}")

    logger.debug(f"Found {len(matches)} matches for git {type_}.")
    best_match = min(
        matches,
        key=lambda item: item[1].distance_from_head if item[1] else math.inf,
    )
    logger.info(
        f"Resolved version from git {type_}; "
        f"version={best_match[0]}, ref={best_match[1]}"
    )
    return best_match


def _parse_archive_source(
    content: str, settings: Settings, sources: list[str]
) -> tuple[list[Version], GitReference]:
    if not content or "$Format" in content:
        raise ValueError(
            "Archive file has not been formatted with 'git archive' or similar: "
            f"{content}"
        )

    ref_kwargs: dict[str, Any] = {}

    for pattern in settings.regex_archive:
        for match in re.finditer(pattern, content):
            groups = match.groupdict()
            ref_kwargs.update(
                {
                    key: value
                    for key, value in groups.items()
                    if value is not None
                    and key not in ("major", "minor", "micro", "patch", "bug")
                }
            )

    ref = GitReference(**ref_kwargs)
    versions: list[Version] = []

    for source in sources:
        try:
            if source == "tag" and ref.tag_name:
                versions = _extract_versions(settings.regex_tag, ref.tag_name)
                break
            if source == "branch" and ref.branch_name:
                versions = _extract_versions(settings.regex_branch, ref.branch_name)
                break
            if source == "commit" and ref.commit_message:
                versions = _extract_versions(settings.regex_commit, ref.commit_message)
                break
        except ValueError:
            logger.warning(
                f"Could not extract version from archive for {source}: {ref}"
            )
            continue

    return versions, ref


def _resolve_archive(
    settings: Settings, sources: list[str]
) -> tuple[Version, GitReference]:
    """Resolves version and metadata from an archive file export."""
    if not settings.version_source_archive:
        raise ValueError("No version_source_archive configured.")

    file_path = Path(settings.version_source_archive)
    target = file_path if file_path.is_absolute() else settings.project_root / file_path
    if not target.exists():
        raise ValueError("Version file not found.")

    logger.debug(f"Attempting to resolve version from archive: {target}")
    content = target.read_text(encoding="utf-8")
    versions, ref = _parse_archive_source(content, settings, sources)

    if not versions:
        raise ValueError(
            f"No version found for archive '{target}' using patterns: "
            f"{settings.regex_archive} and sources {sources}"
        )

    version = max(versions)
    logger.info(f"Resolved version from archive; version={version}, ref={ref}")
    return version, ref


def _get_current_commit(repository: GitRepository) -> GitReference:
    return (
        repository.current_commit
        if repository.is_available and repository.current_commit
        else GitReference(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            distance_from_head=0,
            is_head_commit=False,
        )
    )


def _iterate_version_sources(
    sources: list[str],
    settings: Settings,
    repository: GitRepository,
    env: BuildEnvironment,
) -> tuple[Version | None, GitReference | None]:
    reference = None

    for source in sources:
        if source not in ("file", "function", "tag", "branch", "commit"):
            logger.error(f"Unknown source type encountered: {source}")
            raise ValueError(f"Unknown source type: {source}")

        try:
            if source == "file":
                version = _resolve_file(settings)
            elif source == "function":
                version, reference = _resolve_function(settings, repository, env)
            elif source in ("tag", "branch", "commit"):
                version, reference = _resolve_git(
                    cast("Literal['tag', 'branch', 'commit']", source),
                    settings,
                    repository,
                )
        except ValueError as ver_err:
            logger.warning(
                f"Could not resolve version from source '{source}': {ver_err}"
            )
            continue

        if version:
            logger.info(
                f"Successfully resolved version from source '{source}': {version}"
            )
            return version, reference
    return None, None


def _resolve_version_sources(
    sources: list[str],
    settings: Settings,
    repository: GitRepository,
    env: BuildEnvironment,
) -> tuple[Version, GitReference]:
    version: Version | None = None
    reference: GitReference | None = None

    try:
        version = _resolve_explicit(settings)
        logger.info(f"Resolved version from explicit config/argument: {version}")
        return version, _get_current_commit(repository)
    except ValueError as exp_err:
        logger.info(
            f"Could not resolve version from explicit config/argument: {exp_err}"
        )

    if "auto" in sources:
        sources = [
            "file",
            "function",
            "tag",
            "branch",
            "commit",
        ]
        logger.debug(f"Expanded 'auto' source type to: {sources}")

    logger.info(f"Resolving version sources in order: {sources}")
    version, reference = _iterate_version_sources(sources, settings, repository, env)

    if not version:
        logger.info(
            "No version could be resolved from the configured sources, "
            "attempting to resolve from archive."
        )
        try:
            version, reference = _resolve_archive(settings, sources)
            logger.info(f"Resolved version from archive: {version} for {reference}")
        except ValueError as archive_err:
            logger.info(f"Could not resolve version from archive: {archive_err}")

    if not version:
        version = Version("0.1.0")
        logger.warning(
            f"No version found from any sources, defaulting to base version: {version}"
        )

    if not reference:
        reference = _get_current_commit(repository)
        logger.info(f"Resolved reference to fallback/current commit: {reference}")

    return version, reference


def _get_dirty_files(repository: GitRepository, settings: Settings) -> list[str]:
    """Returns a list of dirty files, excluding configured output files."""
    if not repository.is_available:
        return []

    dirty_files = repository.dirty_files
    if not dirty_files:
        return []

    ignored_paths = set()
    for path_str in [
        (
            settings.output
            if settings.output not in ("sys.stdout", "sys.stderr")
            else None
        ),
        settings.version_source_file,
        *settings.dirty_ignore,
    ]:
        if path_str:
            path = Path(path_str)
            target = path if path.is_absolute() else settings.src_root / path
            ignored_paths.add(target.resolve())

    return [
        file_path
        for file_path in dirty_files
        if (repository.base_path / file_path).resolve() not in ignored_paths
    ]


def resolve_version(
    settings: Settings, repository: GitRepository, environment: BuildEnvironment
) -> tuple[Version, GitReference]:
    """
    Computes the PEP 440 version based on configuration and repository state.

    This function coordinates the resolution of version sources according to the
    provided settings, performs auto-increments if necessary, and formats the final
    version string based on the target build type (e.g., release, dev, alpha).

    Example:
        >>> version, reference = resolve_version(settings, repo, env)

    :param settings: Configuration rules for resolving the version.
    :param repository: The current git repository state.
    :param environment: Build environment metadata.
    :return: A tuple containing the resolved Version and the Git reference object.
    :raises ValueError: If an unknown source type or git type is encountered.
    """

    logger.debug(
        f"resolving version for {settings} in repo={repository} env={environment}"
    )
    base_version, reference = _resolve_version_sources(
        settings.source_type, settings, repository, environment
    )
    logger.info(f"Resolved base version: {base_version} for git reference {reference}")

    # Determine version type to build (release, dev, alpha, post)
    version_type = str(settings.version_type).strip().lower()
    distance = reference.distance_from_head if repository.is_available else 0
    if version_type == "auto":
        if not repository.is_available and reference.commit_sha:
            on_head = True
            is_dirty = False
        else:
            on_head = repository.is_available and reference.is_head_commit
            dirty_files = _get_dirty_files(repository, settings)
            is_dirty = len(dirty_files) > 0

        version_type = "release" if on_head and not is_dirty else "dev"
        logger.info(
            f"Auto-resolved version type to: '{version_type}' "
            f"for ref {reference} and repo {repository}"
        )

    target_str = str(
        settings.auto_increment.get(
            cast(
                "Literal['release', 'dev', 'pre', 'alpha', 'nightly', 'post']",
                version_type,
            ),
            "",
        )
        if settings.auto_increment
        else ""
    ).lower()
    target_idx = {"major": 0, "minor": 1, "micro": 2, "patch": 2}.get(target_str)

    if target_idx is not None and distance > 0:
        parts = [base_version.major, base_version.minor, base_version.micro]
        parts[target_idx] += 1
        for index in range(target_idx + 1, len(parts)):
            parts[index] = 0

        version = Version(".".join(map(str, parts)))
        logger.info(
            f"Auto-incremented version from {base_version} to {version} "
            f"(target='{target_str}')"
        )
    else:
        version = base_version

    context = {
        "version": version,
        "repo": repository,
        "config": settings,
        "env": environment,
        "ref": reference,
    }

    main_version = str(
        render(generate_template(settings.format_main, context, use_eval=True))
    )
    segment = ""
    if version_type == "dev":
        segment = str(
            render(generate_template(settings.format_dev, context, use_eval=True))
        )
    elif version_type in ("pre", "alpha", "nightly"):
        segment = str(
            render(generate_template(settings.format_pre, context, use_eval=True))
        )
    elif version_type == "post":
        segment = str(
            render(generate_template(settings.format_post, context, use_eval=True))
        )

    final_version = Version(f"{main_version}.{segment}".rstrip("+."))
    logger.info(f"Resolved final version: {final_version}")

    return final_version, reference


def _get_version_file_pattern(format_name: str) -> str:
    """Gets the regex pattern for a known configuration file format."""
    if format_name == "cargo":
        # Target version = "..." under [package] or [workspace.package]
        return (
            r"(?s)(\[(?:workspace\.)?package\].*?^version\s*=\s*)"
            r"([\"'])(?P<version>.*?)\2"
        )
    if format_name == "pyproject":
        # Target version = "..." under [project]
        return (
            r"(?s)(^\[project\].*?^version\s*=\s*)"
            r"([\"'])(?P<version>.*?)\2"
        )
    return format_name


MAX_PATH_LENGTH = 255


def _resolve_template_or_regex(
    value: str, project_root: Path
) -> tuple[str, Literal["template", "regex"]]:
    """Helper to classify a configuration pattern value as template/regex."""
    # 1. Check if it's a known alias
    if value == "template":
        return "template", "template"
    if value in ("cargo", "pyproject"):
        return value, "regex"

    # 2. Check if it's a file path that exists
    if "\n" not in value and len(value) <= MAX_PATH_LENGTH and "\x00" not in value:
        try:
            path = Path(value)
            if not path.is_absolute():
                path = project_root / path
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                # If content contains (?P<version>, treat it as regex
                if "(?P<version>" in content:
                    return content, "regex"
                else:
                    return content, "template"
        except OSError:
            pass

    # 3. Check if it's a regex directly (e.g. contains named group (?P<version>)
    if "(?P<version>" in value:
        return value, "regex"

    # 4. Otherwise it's a template string (which might contain formatting tags)
    return value, "template"


def resolve_template_and_mode(
    pattern_val: str,
    output: str,
    project_root: Path,
) -> tuple[str, Literal["template", "regex"]]:
    """Resolves pattern content and execution mode (template vs regex)."""
    # If the pattern value is one of the default templates,
    # and output is a known file format, auto-detect pattern type.
    is_default_template = (
        pattern_val.strip().startswith('"""')
        and "Auto-generated version file from git-versioned" in pattern_val
    )
    if is_default_template:
        out_name = Path(output).name.lower()
        if out_name == "cargo.toml":
            pattern_val = "cargo"
        elif out_name == "pyproject.toml":
            pattern_val = "pyproject"

    return _resolve_template_or_regex(pattern_val, project_root)


def _generate_template_content(
    pattern_content: str,
    version: Version,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> str:
    """Render the pattern content as a template string."""
    context = {
        "version": version,
        "repo": repository,
        "config": settings,
        "env": environment,
        "ref": reference,
    }
    tmpl = generate_template(pattern_content, context, use_eval=True)
    return str(render(tmpl))


def _resolve_stdout_input_path(pattern_content: str, project_root: Path) -> Path:
    """Determine the input file to inject version into when outputting to stdout."""
    if pattern_content == "cargo":
        return project_root / "Cargo.toml"
    if pattern_content == "pyproject":
        return project_root / "pyproject.toml"
    for name in ("pyproject.toml", "Cargo.toml", "setup.cfg"):
        p = project_root / name
        if p.exists():
            return p
    msg = (
        "Could not determine input file to inject version into "
        "when outputting to stdout."
    )
    logger.exception(msg)
    raise FileNotFoundError(msg)


def _generate_regex_content(
    pattern_content: str,
    version: Version,
    settings: Settings,
) -> str:
    """Inject version into source file using regex pattern matching."""
    if settings.output == "sys.stdout":
        input_path = _resolve_stdout_input_path(pattern_content, settings.project_root)
    else:
        input_path = Path(settings.output)
        if not input_path.is_absolute():
            input_path = settings.src_root / input_path

    if not input_path.exists():
        msg = f"Version file to inject into {input_path} does not exist."
        logger.exception(msg)
        raise FileNotFoundError(msg)

    pattern = _get_version_file_pattern(pattern_content)
    file_content = input_path.read_text(encoding="utf-8")

    match = re.search(pattern, file_content, flags=re.MULTILINE)
    if not match:
        msg = f"Could not find matching pattern for version in {input_path}."
        logger.exception(msg)
        raise ValueError(msg)

    try:
        version_span = match.span("version")
    except IndexError as ver_err:
        msg = (
            f"Regex pattern '{pattern_content}' does not contain "
            f"a named capture group '(?P<version>...)'."
        )
        logger.exception(msg)
        raise ValueError(msg) from ver_err

    return (
        file_content[: version_span[0]] + str(version) + file_content[version_span[1] :]
    )


def generate_version_file(
    version: Version,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> Path | None:
    """Writes resolved version metadata to output/stdout/stderr stream.

    This function utilizes the configured pattern to determine whether to
    generate a file from templates, or inject the version into an existing
    file using predefined or custom regex. If settings.output is "sys.stdout",
    the output is written directly to standard output.

    :param version: The resolved PEP 440 version object.
    :param reference: The resolved Git reference object.
    :param settings: Configuration rules for resolving the version.
    :param repository: The current git repository state.
    :param environment: Build environment metadata.
    :return: Path to written file, or None if written to stdout/stderr.
    """
    logger.debug(
        f"generate_version_file called for version={version} reference={reference} "
        f"settings={settings} repository={repository} environment={environment}"
    )

    if not settings.output:
        logger.debug(
            "No output target configured, skipping generation of version file."
        )
        return None

    # Choose template pattern based on dev or release build
    pattern_val = (
        settings.pattern_dev if version.dev is not None else settings.pattern_release
    )

    pattern_content, mode = resolve_template_and_mode(
        pattern_val, settings.output, settings.project_root
    )

    if mode == "template":
        content = _generate_template_content(
            pattern_content, version, reference, settings, repository, environment
        )
    else:
        content = _generate_regex_content(pattern_content, version, settings)

    # Write content to output destination (stdout, stderr, or file)
    if settings.output == "sys.stdout":
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        return None
    elif settings.output == "sys.stderr":
        sys.stderr.write(content)
        if not content.endswith("\n"):
            sys.stderr.write("\n")
        sys.stderr.flush()
        return None
    else:
        output_path = Path(settings.output)
        if not output_path.is_absolute():
            output_path = settings.src_root / output_path

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            logger.info(f"Updated version {version} into {output_path}")
            return output_path
        except Exception as error:
            logger.exception(f"Failed to update file at {output_path}: {error}")
            raise


def resolve_and_generate_version(
    settings: Settings, repository: GitRepository, environment: BuildEnvironment
) -> tuple[Version, Path | None]:
    """
    Main entry point to resolve the version and write the output file if configured.

    This function wraps the core version resolution logic and subsequently triggers
    the generation of the version python file if an output file is specified in the
    settings. It provides a convenient single call for build hooks and integrations.

    Example:
        >>> version, path = resolve_and_generate_version(settings, repo, env)

    :param settings: Configuration rules for resolving the version.
    :param repository: The current git repository state.
    :param environment: Build environment metadata.
    :return: A tuple of the resolved Version and output Path (if generated).
    """
    logger.debug(
        f"resolve_and_generate_version called for {settings} with "
        f"repo={repository} env={environment}"
    )
    version, reference = resolve_version(settings, repository, environment)
    output_path = generate_version_file(
        version, reference, settings, repository, environment
    )

    return version, output_path
