#!/usr/bin/env bash
# Copyright 2026 markurtz
# SPDX-License-Identifier: Apache-2.0
#
# The step behind action.yml. Inputs arrive as environment variables, never
# pasted into the script, so a pull request title cannot run as shell code:
#   INPUT_COMMAND  command and options, split on spaces (default: version)
#   INPUT_TITLE    one extra argument, passed as is (optional)
#   INPUT_VERSION  gitversioned version to run (optional)
# It writes `version` and `output` to $GITHUB_OUTPUT.
set -euo pipefail

spec="gitversioned${INPUT_VERSION:+==${INPUT_VERSION}}"
if command -v uvx >/dev/null 2>&1; then
	runner=(uvx --quiet --from "$spec" gitversioned)
elif command -v pipx >/dev/null 2>&1; then
	runner=(pipx run --spec "$spec" gitversioned)
else
	python3 -m pip install --quiet --user "$spec"
	runner=(python3 -m gitversioned)
fi

read -r -a args <<<"${INPUT_COMMAND:-version}"
if [ -n "${INPUT_TITLE:-}" ]; then
	args+=("$INPUT_TITLE")
fi

status=0
output=$("${runner[@]}" "${args[@]}") || status=$?
printf '%s\n' "$output"
version=$("${runner[@]}" version 2>/dev/null || true)

if [ -n "${GITHUB_OUTPUT:-}" ]; then
	delimiter="gitversioned_$RANDOM$RANDOM"
	{
		printf 'version=%s\n' "$version"
		printf 'output<<%s\n%s\n%s\n' "$delimiter" "$output" "$delimiter"
	} >>"$GITHUB_OUTPUT"
fi
exit "$status"
