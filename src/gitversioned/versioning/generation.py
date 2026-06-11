"""Format and generate output version strings.

Provides utilities to format versions under standards like PEP 440 and SemVer 2,
render version templates using Git repository metadata, and execute strategies to
inject version strings into files or output streams.
"""

from __future__ import annotations

import re

from packaging.version import Version
from tstr import generate_template, render

from gitversioned.logging import autolog
from gitversioned.settings import (
    RegexStrategy,
    Settings,
    TemplatePathStrategy,
    TemplateStrStrategy,
    VersionType,
)
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository

__all__ = [
    "FormattedVersion",
    "generate_from_template",
    "generate_output_from_strategies",
]


class FormattedVersion(Version):
    """Version subclass providing custom string formatting.

    Wraps a packaging Version to custom-format string output for PEP 440 and
    SemVer 2 standards based on the resolved version type.

    Example:
        >>> from packaging.version import Version
        >>> ver = FormattedVersion(Version("1.0.0.post1"), "post", "semver2")
        >>> str(ver)
        '1.0.0-post1'
    """

    def __init__(
        self,
        version: Version,
        version_type: VersionType,
        version_standard: str = "pep440",
    ) -> None:
        """Initialize the formatted version wrapper.

        :param version: The base packaging Version object.
        :param version_type: The type of version being represented.
        :param version_standard: The target version standard ("pep440" or "semver2").
        """
        super().__init__(str(version))
        self._version_type = version_type
        self._version_standard = version_standard

    def __str__(self) -> str:
        """Return the version formatted according to the standard.

        :return: The formatted version string.
        :raises ValueError: If the version standard is unsupported.
        """
        if self._version_standard == "pep440":
            return super().__str__()

        if self._version_standard == "semver2":
            formatted = ".".join(map(str, (list(self.release) + [0, 0])[:3]))
            if self._version_type == "post":
                post_value = self.post or 0
                formatted += f"-post{post_value}"
            elif self._version_type in ("pre", "alpha", "nightly"):
                pre_parts = self.pre or ("a", 0)
                formatted += f"{pre_parts[0]}{pre_parts[1]}"
            elif self._version_type == "dev":
                dev_value = self.dev or 0
                formatted += f"-dev{dev_value}"
            if self.local is not None:
                formatted += f"+{self.local}"
            return formatted

        raise ValueError(f"Unsupported version standard: {self._version_standard}")

    def __repr__(self) -> str:
        """Return the developer-friendly string representation of the formatted version.

        :return: The string representation.
        """
        return repr(self.__str__())


@autolog
def generate_from_template(
    pattern: str | None,
    version: Version,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> str:
    """Render a template pattern using version and git repository metadata.

    Example:
        >>> from gitversioned.settings import Settings
        >>> from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
        >>> from packaging.version import Version
        >>> generate_from_template(
        ...     "v{version}-{ref.short_sha}",
        ...     Version("1.0.0"),
        ...     GitReference(short_sha="abc1234"),
        ...     Settings(),
        ...     GitRepository(),
        ...     BuildEnvironment()
        ... )
        'v1.0.0-abc1234'

    :param pattern: The template string pattern to render.
    :param version: The target Version object.
    :param reference: The active Git reference metadata.
    :param settings: Active application configuration.
    :param repository: The Git repository context helper.
    :param environment: The environment build variables context.
    :return: The rendered string, or an empty string if pattern is empty.
    """
    if not pattern:
        return ""

    context = {
        "version": version,
        "repo": repository,
        "config": settings,
        "env": environment,
        "ref": reference,
    }

    return str(render(generate_template(pattern, context, use_eval=True)))


@autolog
def generate_output_from_strategies(
    version: Version,
    version_type: VersionType,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> str:
    """Resolve the configuration output strategy to generate formatted version content.

    Example:
        >>> from packaging.version import Version
        >>> from gitversioned.settings import Settings, TemplateStrStrategy
        >>> from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
        >>> settings = Settings(
        ...     output_strategies=TemplateStrStrategy(
        ...         content="__version__ = '{version}'"
        ...     )
        ... )
        >>> generate_output_from_strategies(
        ...     Version("1.0.0"),
        ...     "release",
        ...     GitReference(),
        ...     settings,
        ...     GitRepository(),
        ...     BuildEnvironment(),
        ... )
        "__version__ = '1.0.0'"

    :param version: The target Version object.
    :param version_type: The category of version being built.
    :param reference: The current Git reference metadata.
    :param settings: Active application configuration.
    :param repository: The Git repository context helper.
    :param environment: The environment build variables context.
    :return: The generated version string content.
    :raises ValueError: If the active strategy is unsupported or cannot be resolved.
    """
    if isinstance(
        settings.output_strategies,
        (TemplatePathStrategy, TemplateStrStrategy, RegexStrategy),
    ):
        strategy = settings.output_strategies
    elif isinstance(settings.output_strategies, dict):
        if len(settings.output_strategies) == 1:
            strategy = list(settings.output_strategies.values())[0]
        elif version_type in settings.output_strategies:
            strategy = settings.output_strategies[version_type]
        elif "release" in settings.output_strategies:
            strategy = settings.output_strategies["release"]
        else:
            raise ValueError("Could not determine output strategy.")
    else:
        raise ValueError("Could not determine output strategy.")

    if isinstance(strategy, (TemplateStrStrategy, TemplatePathStrategy)):
        return _generate_output_from_template_strategy(
            strategy,
            version,
            version_type,
            reference,
            settings,
            repository,
            environment,
        )

    if isinstance(strategy, RegexStrategy):
        return _generate_output_from_regex_strategy(
            strategy,
            version,
            version_type,
            reference,
            settings,
            repository,
            environment,
        )

    raise ValueError(f"Unsupported strategy type: {type(strategy)}")


@autolog
def _generate_output_from_template_strategy(
    strategy: TemplatePathStrategy | TemplateStrStrategy,
    version: Version,
    version_type: VersionType,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> str:
    # Generate content from a template file or template string strategy.
    if isinstance(strategy, TemplatePathStrategy):
        template_path = settings.resolve_path_from_root(strategy.path)
        if not template_path:
            raise FileNotFoundError(
                f"Template path '{strategy.path}' does not exist in project root "
                f"{settings.project_root} or src root {settings.src_root}."
            )
        content = template_path.read_text(encoding="utf-8")
        strategy = TemplateStrStrategy(content=content)

    if isinstance(strategy, TemplateStrStrategy):
        return generate_from_template(
            strategy.content,
            FormattedVersion(version, version_type, settings.version_standard),
            reference,
            settings,
            repository,
            environment,
        )

    raise ValueError(f"Invalid output strategy type: {type(strategy)}")


@autolog
def _generate_output_from_regex_strategy(
    strategy: RegexStrategy,
    version: Version,
    version_type: VersionType,
    reference: GitReference,
    settings: Settings,
    repository: GitRepository,
    environment: BuildEnvironment,
) -> str:
    # Inject the formatted version into an existing file based on a regex pattern.

    output_path = settings.resolve_path_from_root(settings.output)
    if not output_path:
        raise FileNotFoundError(
            f"Could not resolve content from {settings.output} in project root "
            f"for regex strategy {strategy}."
        )

    content = output_path.read_text(encoding="utf-8")
    matches = list(re.finditer(strategy.pattern, content, flags=re.MULTILINE))
    if not matches:
        raise ValueError(
            f"Regex pattern {strategy.pattern} not found in "
            f"output content from {output_path}."
        )

    formatted_version = FormattedVersion(
        version, version_type, settings.version_standard
    )

    # Process matches in reverse order so modification lengths
    # don't corrupt the index offsets of preceding matches.
    for match in reversed(matches):
        group_dict = match.groupdict()

        if group_dict:
            # Collect and sort named groups inside this single match by their start
            # index in reverse order to prevent inner-match offset shifting.
            named_groups = []
            for name, value in group_dict.items():
                if value is not None:
                    named_groups.append((name, match.start(name), match.end(name)))

            named_groups.sort(key=lambda item: item[1], reverse=True)

            for name, start_idx, end_idx in named_groups:
                # Convert group names like 'ref__tag' to 'ref.tag' for tstr evaluation
                tstr_expression = name.replace("__", ".")
                placeholder = f"{{{tstr_expression}}}"
                rendered_value = generate_from_template(
                    placeholder,
                    formatted_version,
                    reference,
                    settings,
                    repository,
                    environment,
                )
                content = content[:start_idx] + rendered_value + content[end_idx:]
        else:
            # Fallback: if no named capture groups exist, assume the
            # entire regex match represents the version string.
            start_idx, end_idx = match.span()
            rendered_value = generate_from_template(
                "{version}",
                formatted_version,
                reference,
                settings,
                repository,
                environment,
            )
            content = content[:start_idx] + rendered_value + content[end_idx:]

    return content
