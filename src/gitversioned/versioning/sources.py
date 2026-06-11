"""Resolve project version from configured version sources.

This module provides functions to extract and resolve semantic versions from
explicit settings, files, Python functions, Git metadata (tags, branches, commits),
or archives. It processes these sources in a configurable priority order to find
and return a valid PEP 440 version.
"""

from __future__ import annotations

import functools
import importlib
import re as re_module
import sys
from typing import Any, Literal

from packaging.version import Version

from gitversioned.logging import autolog, logger
from gitversioned.settings import Settings
from gitversioned.utils import GitReference, GitRepository

__all__ = [
    "VersionResolutionError",
    "resolve_from_explicit_source",
    "resolve_from_file_source",
    "resolve_from_function_source",
    "resolve_from_git_source",
    "resolve_sources",
    "resolve_sources_from_archive",
]


class VersionResolutionError(ValueError):
    """Exception raised when version resolution fails for a source.

    Indicates that a configured version source (file, function, git, or archive)
    failed to resolve to a valid semantic version. Used to distinguish resolution
    failures from general runtime errors.

    Example:
        >>> raise VersionResolutionError("No tag matches version pattern.")
    """


@autolog(exception_log_level="INFO")
def resolve_sources(
    sources: list[str],
    settings: Settings,
    repository: GitRepository,
) -> tuple[Version, GitReference]:
    """Resolve project version by checking configured sources in order.

    Iterates through the requested sources (e.g., 'file', 'tag', 'branch') and
    returns the first resolved version and Git reference. If 'auto' is specified,
    it expands to check all standard sources. Falls back to archive resolution
    if all listed sources fail.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import GitRepository
        >>> settings = Settings()
        >>> repo = GitRepository()
        >>> version, ref = resolve_sources(["tag", "file"], settings, repo)

    :param sources: Priority list of source types to query.
    :param settings: Configuration settings instance.
    :param repository: Git repository wrapper.
    :return: Resolved version and associated Git reference.
    :raises VersionResolutionError: If no version is found in any source.
    """
    try:
        version, reference = resolve_from_explicit_source(settings, repository)
        logger.info(f"Resolved version from explicit config/argument: {version}")
        return version, reference
    except VersionResolutionError as exp_err:
        logger.info(
            f"Could not resolve version from explicit config/argument: {exp_err}"
        )

    had_auto = "auto" in sources
    if had_auto:
        if repository.is_available:
            sources = ["tag", "branch", "commit", "file", "function"]
        else:
            sources = ["file", "function"]
        logger.debug(f"Expanded 'auto' source type to: {sources}")

    logger.info(f"Resolving version sources in order: {sources}")

    resolvers = {
        "file": resolve_from_file_source,
        "function": resolve_from_function_source,
        "tag": functools.partial(resolve_from_git_source, "tag"),
        "branch": functools.partial(resolve_from_git_source, "branch"),
        "commit": functools.partial(resolve_from_git_source, "commit"),
    }

    for source in sources:
        resolver = resolvers.get(source)
        if not resolver:
            raise ValueError(f"Unknown source type: {source}")

        try:
            version, reference = resolver(settings, repository)
            if version:
                logger.info(
                    f"Successfully resolved version from source '{source}': {version}"
                )
                return version, reference
        except VersionResolutionError as ver_err:
            logger.info(f"Could not resolve version from source '{source}': {ver_err}")

    logger.info(
        "No version could be resolved from the configured sources, "
        "attempting to resolve from archive."
    )
    try:
        archive_sources = (
            ["tag", "branch", "commit", "file", "function"] if had_auto else sources
        )
        version, reference = resolve_sources_from_archive(archive_sources, settings)
        logger.info(f"Resolved version from archive: {version} for {reference}")
        return version, reference
    except VersionResolutionError as archive_err:
        logger.info(f"Could not resolve version from archive: {archive_err}")

    raise VersionResolutionError(f"No version found for any of the sources: {sources}")


@autolog(exception_log_level="INFO")
def resolve_from_explicit_source(
    settings: Settings, repository: GitRepository
) -> tuple[Version, GitReference]:
    """Resolve version from an explicit configuration version string.

    Extracts a static version from settings, checking it against configured
    regex patterns. Rejects dynamic aliases like 'auto', 'dynamic', or '0.0.0'.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import GitRepository
        >>> settings = Settings(version="1.2.3")
        >>> repo = GitRepository()
        >>> version, ref = resolve_from_explicit_source(settings, repo)

    :param settings: Configuration settings containing the version string.
    :param repository: Target Git repository.
    :return: Resolved version and the current Git commit or fallback reference.
    :raises VersionResolutionError: If the version is unset or is a dynamic alias.
    """
    version_str = str(settings.version).strip().lower()
    if version_str in ("auto", "dynamic", "0.0.0", ""):
        raise VersionResolutionError(
            f"Explicit version is not set; value "
            f"'{version_str}' is not a valid version."
        )
    version = _extract_versions(list(settings.regex_version), version_str)[0]
    logger.info(f"Resolved explicit version: {version}")

    return version, repository.current_commit_or_fallback


@autolog(exception_log_level="INFO")
def resolve_from_file_source(
    settings: Settings, repository: GitRepository
) -> tuple[Version, GitReference]:
    """Resolve version by parsing a configured version source file.

    Reads the path specified in settings, matches its contents against file regex
    patterns, and extracts the first matching version.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import GitRepository
        >>> settings = Settings(version_source_file="setup.cfg")
        >>> repo = GitRepository()
        >>> version, ref = resolve_from_file_source(settings, repo)

    :param settings: Configuration settings specifying file path and regex.
    :param repository: Target Git repository.
    :return: Resolved version and current Git commit or fallback reference.
    :raises VersionResolutionError: If the file is missing, unreadable, or unmatched.
    """
    if not settings.version_source_file:
        logger.debug("No version_source_file configured.")
        raise VersionResolutionError("No version_source_file configured.")

    source_path = settings.resolve_path_from_root(settings.version_source_file)

    if (not source_path or not source_path.exists()) and (
        not repository.is_available and settings.output
    ):
        output_path = settings.resolve_path_from_root(settings.output)
        if output_path and output_path.exists():
            source_path = output_path
            logger.debug(
                f"Version source file '{settings.version_source_file}' "
                f"not found; falling back to output file: {source_path}"
            )

    if not source_path or not source_path.exists():
        raise VersionResolutionError(
            f"Neither version_source_file "
            f"'{settings.version_source_file}' nor "
            f"output file '{settings.output}' found."
        )

    logger.debug(f"Attempting to resolve version from file: {source_path}")

    try:
        content = source_path.read_text(encoding="utf-8")
    except OSError as read_err:
        raise VersionResolutionError(
            f"Failed to read version file '{source_path}': {read_err}"
        ) from read_err

    version = _extract_versions(list(settings.regex_file), content)[0]
    logger.info(
        f"Resolved version from file '{source_path}' using pattern "
        f"{settings.regex_file}: {version}"
    )
    return version, repository.current_commit_or_fallback


def _execute_version_function(
    function_str: str, settings: Settings, repository: GitRepository
) -> tuple[Version, GitReference]:
    """Helper to dynamically import and execute the user-defined version function."""
    module_name, function_name = function_str.split(":", 1)
    if not all(part.isidentifier() for part in module_name.split(".")):
        raise ValueError(f"Invalid module name: '{module_name}'")
    # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
    module = importlib.import_module(module_name)
    version, reference = getattr(module, function_name)(
        settings=settings, repo=repository
    )
    if not version or not isinstance(version, Version):
        raise ValueError(
            f"Version function '{function_str}' did not "
            f"return a valid version. Got: {version}"
        )
    if not reference or not isinstance(reference, GitReference):
        raise ValueError(
            f"Version function '{function_str}' did not "
            f"return a valid reference. Got: {reference}"
        )
    return version, reference


@autolog(exception_log_level="INFO")
def resolve_from_function_source(
    settings: Settings, repository: GitRepository
) -> tuple[Version, GitReference]:
    """Resolve version by executing a custom Python function.

    Dynamically imports and calls a user-defined function in the format
    'module:function', passing settings and repository as keyword arguments.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import GitRepository
        >>> settings = Settings(version_source_function="my_module:get_version")
        >>> repo = GitRepository()
        >>> version, ref = resolve_from_function_source(settings, repo)

    :param settings: Configuration settings containing the function path.
    :param repository: Target Git repository.
    :return: Reconciled version and associated Git reference returned by the function.
    :raises VersionResolutionError: If the function path is invalid or execution fails.
    :raises ValueError: If the function returns an invalid version or reference type.
    """
    if not settings.version_source_function:
        logger.debug("No version_source_function configured.")
        raise VersionResolutionError("No version_source_function configured.")

    function_str = str(settings.version_source_function)
    if ":" not in function_str:
        raise VersionResolutionError(
            f"Invalid function format: '{function_str}'. "
            "Must be in format 'module:function'."
        )

    logger.debug(f"Attempting to resolve version from function: {function_str}")

    # Insert into PATH to allow general importing within the package
    added_paths = []
    for path in [str(settings.project_root), str(settings.src_root)]:
        if path not in sys.path:
            sys.path.insert(0, path)
            added_paths.append(path)

    try:
        version, reference = _execute_version_function(
            function_str, settings, repository
        )
        logger.info(
            f"Resolved version and reference from function "
            f"{function_str}: {version} ({reference})"
        )
        return version, reference
    except Exception as error:
        logger.exception(f"Version function '{function_str}' failed: {error}")
        raise
    finally:
        for path in added_paths:
            if path in sys.path:
                sys.path.remove(path)


@autolog(exception_log_level="INFO")
def resolve_from_git_source(
    type_: Literal["tag", "branch", "commit"],
    settings: Settings,
    repository: GitRepository,
) -> tuple[Version, GitReference]:
    """Resolve version from Git metadata (tags, branch name, or commit messages).

    Extracts version candidates from the specified Git metadata type using regex
    patterns and selects the match closest to the HEAD commit.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import GitRepository
        >>> settings = Settings()
        >>> repo = GitRepository()
        >>> version, ref = resolve_from_git_source("tag", settings, repo)

    :param type_: Git metadata category to query ('tag', 'branch', or 'commit').
    :param settings: Configuration settings containing the regex patterns.
    :param repository: Target Git repository.
    :return: Resolved version and the closest matching Git reference.
    :raises VersionResolutionError: If Git is unavailable or no patterns match.
    :raises ValueError: If the metadata type is invalid.
    """
    if not repository.is_available:
        raise VersionResolutionError("No git repository available.")

    candidates: list[tuple[str, GitReference]] = []
    patterns: list[str] = []

    if type_ == "tag":
        patterns = list(settings.regex_tag)
        candidates = [(tag.tag_name, tag) for tag in repository.tags]
    elif type_ == "branch":
        patterns = list(settings.regex_branch)
        if repository.current_branch:
            candidates = [
                (
                    repository.current_branch.branch_name,
                    repository.current_branch,
                )
            ]
    elif type_ == "commit":
        patterns = list(settings.regex_commit)
        candidates = [(commit.commit_message, commit) for commit in repository.commits]
    else:
        raise ValueError(f"Invalid git type: {type_}")

    matches: list[tuple[Version, GitReference]] = []
    for text, reference in candidates:
        try:
            version = _extract_versions(patterns, text)[0]
            matches.append((version, reference))
        except VersionResolutionError as ver_err:
            logger.warning(
                f"Could not extract version from git {type_} '{text}' using "
                f"patterns {patterns}: {ver_err}"
            )
            continue

    if not matches:
        raise VersionResolutionError(
            f"No version found for git {type_} using patterns {patterns}"
        )

    logger.debug(f"Found {len(matches)} matches for git {type_}.")
    best_match = min(
        matches,
        key=lambda item: item[1].distance_from_head,
    )
    logger.info(
        f"Resolved version from git {type_}; "
        f"version={best_match[0]}, ref={best_match[1]}"
    )
    return best_match


@autolog(exception_log_level="INFO")
def resolve_sources_from_archive(
    sources: list[str], settings: Settings
) -> tuple[Version, GitReference]:
    """Resolve version from a git-archive export description file.

    Parses the archival export file, extracts Git metadata (tags, branches, commits)
    via regex, reconstructs a GitReference, and extracts versions matching the
    specified source types.

    Example:
        >>> from gitversioned.settings import Settings
        >>> settings = Settings(version_source_archive=".git_archival.txt")
        >>> version, ref = resolve_sources_from_archive(["tag"], settings)

    :param sources: Source types to query from the reconstructed Git metadata.
    :param settings: Configuration settings.
    :return: Resolved version and reconstructed Git reference.
    :raises VersionResolutionError: If the archive file is missing, raw, or unmatched.
    """
    archive_path = settings.resolve_path_from_root(settings.version_source_archive)
    if not archive_path or not archive_path.exists():
        raise VersionResolutionError(
            f"Version file not found for source {settings.version_source_archive}"
        )

    logger.debug(f"Attempting to resolve version from archive: {archive_path}")
    try:
        content = archive_path.read_text(encoding="utf-8")
    except OSError as read_err:
        raise VersionResolutionError(
            f"Failed to read archive file '{archive_path}': {read_err}"
        ) from read_err

    if not content or "$Format" in content:
        raise VersionResolutionError(
            "Archive file has not been formatted with 'git archive' or similar: "
            f"{content}"
        )

    ref_kwargs: dict[str, Any] = {}
    for pattern in settings.regex_archive:
        for match in re_module.finditer(pattern, content):
            ref_kwargs.update(
                {
                    key: value
                    for key, value in match.groupdict().items()
                    if value and key not in {"major", "minor", "micro", "patch", "bug"}
                }
            )

    reference = GitReference.model_validate(ref_kwargs)
    dispatch = {
        "tag": (reference.tag_name, list(settings.regex_tag)),
        "branch": (reference.branch_name, list(settings.regex_branch)),
        "commit": (reference.commit_message, list(settings.regex_commit)),
    }

    versions: list[Version] = []
    for source in sources:
        attr_val, pattern = dispatch.get(source, ("", []))
        if attr_val and pattern:
            try:
                versions = _extract_versions(pattern, attr_val)
                break
            except ValueError:
                logger.warning(f"Could not extract version from {source}: {reference}")

    if not versions:
        raise VersionResolutionError(
            f"No version found for archive '{archive_path}' using patterns: "
            f"{settings.regex_archive} and sources {sources}"
        )

    version = max(versions)
    logger.info(f"Resolved version from archive; version={version}, ref={reference}")
    return version, reference


# Helper to extract version objects matching regex patterns from input text.
def _extract_versions(patterns: list[str], text: str) -> list[Version]:
    versions: list[Version] = []
    for pattern in patterns:
        for match in re_module.finditer(str(pattern), text):
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
        raise VersionResolutionError(
            f"No version found for patterns {patterns} and text {text}"
        )

    return versions
