#!/usr/bin/env bash

# Print the dynamically resolved version using a custom release pattern
echo "1. Resolving version and printing with custom prefix:"
gitversioned --output sys.stdout --pattern-release "APP_VERSION={version}" --pattern-dev "APP_VERSION={version}"

# Showcase injecting version dynamically into docker build using CLI stdout
echo ""
echo "2. Dynamic version injection into Docker Build (dry-run command):"
echo "docker build --build-arg VERSION=\$(gitversioned --output sys.stdout --pattern-release \"{version}\" --pattern-dev \"{version}\") ."
