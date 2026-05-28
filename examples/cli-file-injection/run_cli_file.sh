#!/usr/bin/env bash

# Setup dummy files
cp Cargo.toml.template Cargo.toml
cp pyproject.toml.template pyproject.toml

echo "Before Injection:"
echo "--- Cargo.toml ---"
cat Cargo.toml
echo "--- pyproject.toml ---"
cat pyproject.toml

# Run GitVersioned CLI to update Cargo.toml
gitversioned --output Cargo.toml --version-type release

# Run GitVersioned CLI to update pyproject.toml
gitversioned --output pyproject.toml --version-type release

echo ""
echo "After Injection:"
echo "--- Cargo.toml ---"
cat Cargo.toml
echo "--- pyproject.toml ---"
cat pyproject.toml

# Cleanup
rm Cargo.toml pyproject.toml
