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
import itertools
import re
import sys
from pathlib import Path
from typing import Literal, cast

from loguru import logger
from packaging.version import InvalidVersion, Version
from tstr import generate_template, render

from gitversioned.settings import Settings
from gitversioned.utils import Branch, BuildEnvironment, Commit, GitRepository, Tag

__all__ = [
    "DirtyRepositoryError",
    "generate_version_py",
    "resolve_and_generate_version",
    "resolve_version",
]


class DirtyRepositoryError(Exception):
    """
    Raised when the repository has uncommitted changes.

    This exception is utilized to halt the build process when strict versioning
    rules enforce that no uncommitted changes are present in the working directory.

    Example:
        >>> if repository.is_dirty:
        ...     raise DirtyRepositoryError("Working directory is dirty")
    """


def _extract_version_from_match(match: re.Match[str]) -> Version:
    """Extracts a Version object from a regex match group dictionary or groups."""
    groups = match.groupdict()
    major = groups.get("major")
    minor = groups.get("minor")
    micro = groups.get("micro") or groups.get("patch")

    if major is None or minor is None or micro is None:
        raise InvalidVersion("Invalid version string")

    return Version(f"{major}.{minor}.{micro}")


def _resolve_explicit(settings: Settings) -> Version | None:
    """Checks if a hardcoded version is provided in settings."""
    version_str = str(settings.version).strip().lower()
    logger.debug(f"Evaluating explicit version setting: '{version_str}'")
    if version_str in ("auto", "dynamic", "0.0.0", ""):
        return None
    version = Version(version_str)
    logger.info(f"Resolved explicit version: {version}")
    return version


def _resolve_file(settings: Settings) -> Version | None:
    """Resolves version from the configured version file."""
    if not settings.version_source_file:
        logger.debug("No version_source_file configured.")
        return None

    file_path = Path(settings.version_source_file)
    target = file_path if file_path.is_absolute() else settings.src_root / file_path
    logger.debug(f"Attempting to resolve version from file: {target}")

    if not target.exists():
        logger.info(f"Version file not found: {target}")
        return None

    content = target.read_text(encoding="utf-8")
    for pattern in settings.regex_file:
        if match := re.search(str(pattern), content):
            version = _extract_version_from_match(match)
            logger.info(
                f"Resolved version from file '{target}' using pattern "
                f"'{pattern}': {version}"
            )
            return version

    logger.error(
        f"No version found in file '{target}' matching any of the patterns: "
        f"{settings.regex_file}"
    )
    raise ValueError(
        f"No version found in file '{target}' matching any of the patterns: "
        f"{settings.regex_file}"
    )


def _resolve_function(settings: Settings) -> Version | None:
    """Resolves version by executing a configured python function."""
    if not settings.version_source_function:
        logger.debug("No version_source_function configured.")
        return None

    logger.debug(
        f"Attempting to resolve version from function: "
        f"{settings.version_source_function}"
    )
    try:
        module_name, function_name = str(settings.version_source_function).split(":", 1)

        # Insert into PATH to allow general importing within the package
        added_paths = []
        for path in [str(settings.project_root), str(settings.src_root)]:
            if path not in sys.path:
                sys.path.insert(0, path)
                added_paths.append(path)

        try:
            module = importlib.import_module(module_name)
            result = getattr(module, function_name)()
            version = Version(str(result))
            logger.info(
                f"Resolved version from function '{settings.version_source_function}': "
                f"{version}"
            )
            return version
        finally:
            for path in added_paths:
                if path in sys.path:
                    sys.path.remove(path)
    except Exception as error:
        logger.exception(
            f"Version function '{settings.version_source_function}' failed: {error}"
        )
        raise


def _resolve_git(
    type_: Literal["tag", "branch", "commit"],
    settings: Settings,
    repository: GitRepository,
) -> tuple[Version | None, Branch | Commit | Tag | None]:
    """Generic logic for matching Git objects against regex patterns."""
    logger.debug(f"Attempting to resolve version from git {type_}")

    if not repository.is_available:
        logger.warning("No git repository available.")
        return None, None

    candidates: list[tuple[str, Branch | Commit | Tag | None]] = []
    try:
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
            candidates = [
                (commit.commit_message, commit) for commit in repository.commits
            ]
        else:
            raise ValueError(f"Invalid git type: {type_}")
    except Exception as error:
        logger.exception(f"Failed to resolve version from git {type_}: {error}")
        raise

    matches: list[tuple[Version, Branch | Commit | Tag | None]] = []
    for (text, reference), pattern in itertools.product(candidates, patterns):
        if match := re.search(str(pattern), text):
            try:
                matches.append((_extract_version_from_match(match), reference))
                break
            except InvalidVersion as ver_err:
                logger.warning(
                    f"Extracted invalid version from {type_} text '{text}' "
                    f"using pattern '{pattern}': {ver_err}"
                )
                continue

    if matches:
        logger.debug(f"Found {len(matches)} matches for git {type_}.")
        best_match = min(
            matches,
            key=lambda item: item[1].distance_from_head if item[1] else 0,
        )
        logger.info(f"Resolved version from git {type_}: {best_match[0]}")
        return best_match

    logger.debug(f"No version matches found for git {type_}.")
    return None, None


def _get_current_commit(repository: GitRepository) -> Commit:
    return (
        repository.current_commit
        if repository.is_available and repository.current_commit
        else Commit(
            commit_sha="",
            short_sha="",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            distance_from_head=0,
            is_head_commit=False,
            author_name="",
            author_email="",
            commit_message="",
        )
    )


def _resolve_version_sources(
    sources: list[str], settings: Settings, repository: GitRepository
) -> tuple[Version, Branch | Commit | Tag]:
    if version := _resolve_explicit(settings):
        logger.info(f"Resolved version from explicit config/argument: {version}")
        return version, _get_current_commit(repository)

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
    reference = None
    version = None

    for source in sources:
        if source == "file":
            version = _resolve_file(settings)
        elif source == "function":
            version = _resolve_function(settings)
        elif source in ("tag", "branch", "commit"):
            version, reference = _resolve_git(
                cast("Literal['tag', 'branch', 'commit']", source),
                settings,
                repository,
            )
        else:
            logger.error(f"Unknown source type encountered: {source}")
            raise ValueError(f"Unknown source type: {source}")

        if version:
            logger.info(
                f"Successfully resolved version from source '{source}': {version}"
            )
            break

    if not version:
        version = Version("0.1.0")
        logger.warning(
            f"No version found from sources, defaulting to base version: {version}"
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
    for path_str in (settings.output_file, settings.version_source_file):
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
) -> tuple[Version, Commit | Tag | Branch]:
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
        settings.source_type, settings, repository
    )
    logger.info(f"Resolved base version: {base_version} for git reference {reference}")

    # Determine version type to build (release, dev, alpha, post)
    version_type = str(settings.version_type).strip().lower()
    distance = reference.distance_from_head if repository.is_available else 0
    if version_type == "auto":
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
    reference: Commit | Tag | Branch,
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
