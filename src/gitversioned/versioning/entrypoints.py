"""
Primary entry points for dynamic version resolution.

Provides high-level functions to resolve PEP 440 versions from Git repository
state, format the version string based on configured templates, and write the
output to target files or system streams.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from packaging.version import Version

from gitversioned.logging import autolog, logger
from gitversioned.settings import Settings, VersionType
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning.generation import (
    generate_from_template,
    generate_output_from_strategies,
)
from gitversioned.versioning.sources import VersionResolutionError, resolve_sources

__all__ = [
    "resolve_version",
    "resolve_version_output",
    "resolve_version_output_to_stream",
]


@autolog
def resolve_version(
    settings: Settings,
    repository: GitRepository | None = None,
    environment: BuildEnvironment | None = None,
) -> tuple[Version, VersionType, GitReference]:
    """
    Resolve the dynamic version from configured sources and apply formatting.

    Queries the repository sources to obtain a base version, determines the build
    type (e.g., release or dev), applies auto-increment increments if configured,
    and formats the final PEP 440 version.

    Example:
        >>> from gitversioned.settings import Settings
        >>> version, v_type, ref = resolve_version(Settings())

    :param settings: Configuration settings governing version resolution.
    :param repository: Optional Git repository instance to query.
    :param environment: Optional build environment parameters.
    :return: A tuple containing the final normalized Version, the version type,
        and the GitReference used for resolution.
    """
    repository, environment = _resolve_repo_and_env(settings, repository, environment)

    try:
        version, reference = resolve_sources(settings.source_type, settings, repository)
        logger.info(f"Resolved version from sources: {version} for git ref {reference}")

    except VersionResolutionError as ver_err:
        logger.info(f"Could not resolve version from sources: {ver_err}")
        version = Version("0.1.0")
        reference = repository.current_commit_or_fallback
        logger.warning(
            "No version could be resolved from the configured sources, "
            f"defaulting to base version: {version} and git reference {reference}"
        )

    version_type = _determine_version_type(settings, repository, reference)
    logger.info(f"Using version type: '{version_type}' for git reference {reference}")

    target_key = cast("VersionType", version_type)
    auto_increment_level = ""
    val = (
        settings.auto_increment.get(cast("Any", target_key))
        if settings.auto_increment is not None
        else None
    )
    if (
        val is None
        and target_key in ("alpha", "nightly")
        and settings.auto_increment is not None
    ):
        val = settings.auto_increment.get("pre")
    if val is not None:
        auto_increment_level = val.lower().strip()
    if (
        target_idx := {"major": 0, "minor": 1, "micro": 2, "patch": 2, "bug": 2}.get(
            auto_increment_level
        )
    ) is not None:
        base_version = version
        parts = [version.major, version.minor, version.micro]
        parts[target_idx] += 1
        for index in range(target_idx + 1, len(parts)):
            parts[index] = 0
        version = Version(".".join(map(str, parts)))
        logger.info(
            f"Auto-incremented version from {base_version} to {version} "
            f"(target='{auto_increment_level}')"
        )

    # Generate and validate new semantic version
    version_base = generate_from_template(
        settings.format_main, version, reference, settings, repository, environment
    )
    version_segment = generate_from_template(
        {
            "release": "",
            "dev": settings.format_dev,
            "pre": settings.format_pre,
            "alpha": settings.format_pre,
            "nightly": settings.format_pre,
            "post": settings.format_post,
        }.get(version_type),
        version,
        reference,
        settings,
        repository,
        environment,
    )
    version_final = Version(f"{version_base}.{version_segment}".rstrip("+."))
    logger.info(f"Resolved final version: {version_final}")

    return version_final, cast("VersionType", version_type), reference


@autolog
def _determine_version_type(
    settings: Settings,
    repository: GitRepository,
    reference: GitReference,
) -> str:
    # Determine version type to build (release, dev, alpha, post)
    version_type = str(settings.version_type).strip().lower()
    if version_type == "auto":
        raw_ignore = [
            settings.output,
            settings.version_source_file,
            *settings.dirty_ignore,
        ]
        if hasattr(settings, "overrides") and settings.overrides:
            for override_data in settings.overrides.values():
                if isinstance(override_data, dict) and "output" in override_data:
                    raw_ignore.append(override_data["output"])
        ignore_paths = [
            path
            for raw_path in raw_ignore
            if (path := settings.resolve_path_from_root(raw_path)) is not None
        ]
        is_dirty = bool(repository.filtered_dirty_files(ignore_paths=ignore_paths))
        version_type = "dev" if is_dirty or not reference.is_head_commit else "release"
        logger.info(
            f"Auto-resolved version type to: '{version_type}' for ref {reference}"
        )
    return version_type


@autolog
def resolve_version_output(
    settings: Settings,
    repository: GitRepository | None = None,
    environment: BuildEnvironment | None = None,
) -> tuple[
    str,
    Version,
    VersionType,
    GitReference,
]:
    """
    Resolve the version and format the target output content.

    Runs version resolution and then applies the configured output strategies
    to format the final string (e.g., for writing to a version file).

    Example:
        >>> from gitversioned.settings import Settings
        >>> content, version, v_type, ref = resolve_version_output(Settings())

    :param settings: Configuration settings governing output generation.
    :param repository: Optional Git repository instance to query.
    :param environment: Optional build environment parameters.
    :return: A tuple containing the formatted output content string, the resolved
        Version, the version type, and the GitReference.
    """
    repository, environment = _resolve_repo_and_env(settings, repository, environment)
    version, version_type, reference = resolve_version(
        settings, repository, environment
    )
    output = generate_output_from_strategies(
        version, version_type, reference, settings, repository, environment
    )
    logger.info(f"Resolved version output: {output} for git reference {reference}")

    return output, version, version_type, reference


@autolog
def resolve_version_output_to_stream(
    settings: Settings,
    repository: GitRepository | None = None,
    environment: BuildEnvironment | None = None,
) -> tuple[Path | None, str, Version, VersionType, GitReference]:
    """
    Resolve the version and write formatted content to the configured output file path.

    Resolves the dynamic version, formats it using the configured strategy, and writes
    the formatted content to the specified output file path. Creates parent directories
    for files if needed.

    Example:
        >>> from gitversioned.settings import Settings
        >>> settings = Settings()
        >>> res = resolve_version_output_to_stream(settings)

    :param settings: Configuration settings governing output path and formatting.
    :param repository: Optional Git repository instance to query.
    :param environment: Optional build environment parameters.
    :return: A tuple containing the resolved output Path (or None if disabled),
        the formatted content, the Version, the version type, and the GitReference.
    :raises ValueError: If the configured output target cannot be written to.
    """
    repository, environment = _resolve_repo_and_env(settings, repository, environment)
    output_content, version, version_type, reference = resolve_version_output(
        settings, repository, environment
    )

    output_path = None
    if not settings.output:
        logger.debug("No output target configured, skipping writing to output path.")
    else:
        output_path = settings.resolve_path_from_root(
            settings.output, enforce_existence=False
        )
        if output_path is None:
            raise ValueError(
                f"Could not resolve output path for target: {settings.output}"
            )
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_content, encoding="utf-8")
        except OSError as err:
            raise ValueError(f"Invalid output target: {settings.output}") from err

    if hasattr(settings, "overrides") and settings.overrides:
        for override_name in settings.overrides:
            override_settings = settings.get_overridden_settings(override_name)
            override_settings.version = str(version)
            override_settings.auto_increment = None
            override_settings.version_type = version_type
            resolve_version_output_to_stream(
                settings=override_settings,
                repository=repository,
                environment=environment,
            )

    return output_path, output_content, version, version_type, reference


def _resolve_repo_and_env(
    settings: Settings,
    repository: GitRepository | None = None,
    environment: BuildEnvironment | None = None,
) -> tuple[GitRepository, BuildEnvironment]:
    # Resolve the repository and environment to use.
    return (
        repository if repository is not None else GitRepository(settings.project_root),
        environment
        if environment is not None
        else BuildEnvironment(project_root=settings.project_root),
    )
