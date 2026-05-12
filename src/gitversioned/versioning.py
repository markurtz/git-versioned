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
    "generate_version_py",
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
        module = importlib.import_module(module_name)
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
        settings.output_file,
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


def generate_version_py(
    version: Version,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> Path | None:
    """
    Writes the resolved version metadata to a python file using templates.

    This function utilizes the configured release or development templates to
    generate a python file containing version information, which can then be
    included directly within the target package.

    Example:
        >>> path = generate_version_py(version, ref, settings, repo, env)

    :param version: The resolved PEP 440 version object.
    :param reference: The resolved Git reference object.
    :param settings: Configuration rules for resolving the version.
    :param repository: The current git repository state.
    :param environment: Build environment metadata.
    :return: The Path object pointing to the written file.
    """
    logger.debug(
        f"generate_version_py called for version={version} reference={reference} "
        f"settings={settings} repository={repository} environment={environment}"
    )

    if not settings.output_file:
        logger.debug("No output file configured, skipping generation of version file.")
        return None

    template = (
        settings.template_dev if version.dev is not None else settings.template_release
    )
    context = {
        "version": version,
        "repo": repository,
        "config": settings,
        "env": environment,
        "ref": reference,
    }
    content = str(render(generate_template(template, context, use_eval=True)))

    try:
        output_path = Path(settings.output_file)
        if not output_path.is_absolute():
            output_path = settings.src_root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Generated version py file successfully at: {output_path}")
    except Exception as error:
        logger.exception(
            f"Failed to write version python file to {output_path}: {error}"
        )
        raise

    return output_path


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
    output_path = generate_version_py(
        version, reference, settings, repository, environment
    )

    return version, output_path
