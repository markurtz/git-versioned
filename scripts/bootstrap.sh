#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — Template Initialization
#
# Automatically replaces all template placeholders (e.g., project_name)
# with your actual project values.
#
# Usage:
#   ./scripts/bootstrap.sh --project-name my-app --organization my-org
# =============================================================================

set -euo pipefail

if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Bootstraps the repository by replacing template variables."
    echo ""
    echo "Options:"
    echo "  --project-name NAME    Replacement for project_name"
    echo "  --project-desc DESC    Replacement for {{project_description}}"
    echo "  --organization ORG     Replacement for {{organization}}"
    echo "  --org-name ORG         Replacement for {{org_name}}"
    echo ""
    echo "Example: $0 --project-name my-app --organization my-org"
    exit 0
fi

PROJECT_NAME=""
PROJECT_DESC=""
ORGANIZATION=""
ORG_NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-name)
            if [[ $# -lt 2 ]] || [[ "$2" == -* ]]; then
                echo "[ERROR] Option $1 requires a value."
                echo "Use $0 --help for usage guidance."
                exit 1
            fi
            PROJECT_NAME="$2"
            shift 2
            ;;
        --project-desc)
            if [[ $# -lt 2 ]] || [[ "$2" == -* ]]; then
                echo "[ERROR] Option $1 requires a value."
                echo "Use $0 --help for usage guidance."
                exit 1
            fi
            PROJECT_DESC="$2"
            shift 2
            ;;
        --organization)
            if [[ $# -lt 2 ]] || [[ "$2" == -* ]]; then
                echo "[ERROR] Option $1 requires a value."
                echo "Use $0 --help for usage guidance."
                exit 1
            fi
            ORGANIZATION="$2"
            shift 2
            ;;
        --org-name)
            if [[ $# -lt 2 ]] || [[ "$2" == -* ]]; then
                echo "[ERROR] Option $1 requires a value."
                echo "Use $0 --help for usage guidance."
                exit 1
            fi
            ORG_NAME="$2"
            shift 2
            ;;
        *)
            echo "[ERROR] Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT_NAME" ]] || [[ -z "$PROJECT_DESC" ]] || [[ -z "$ORGANIZATION" ]] || [[ -z "$ORG_NAME" ]]; then
    echo "[ERROR] Missing required arguments."
    echo "All of the following options must be provided:"
    echo "  --project-name"
    echo "  --project-desc"
    echo "  --organization"
    echo "  --org-name"
    echo ""
    echo "Use $0 --help for usage guidance."
    exit 1
fi

echo "[INFO] Starting repository bootstrap..."

export PROJECT_NAME
export PROJECT_DESC
export ORGANIZATION
export ORG_NAME

python3 -c "
import os, sys, shutil

project_name = os.environ.get('PROJECT_NAME', '')
python_pkg = project_name.replace('-', '_')

replacements = {
    '{{project_name}}': project_name,
    '%7B%7Bproject_name%7D%7D': project_name,
    'project_name': python_pkg,
    '{{project_description}}': os.environ.get('PROJECT_DESC', ''),
    '%7B%7Bproject_description%7D%7D': os.environ.get('PROJECT_DESC', ''),
    '{{organization}}': os.environ.get('ORGANIZATION', ''),
    '%7B%7Borganization%7D%7D': os.environ.get('ORGANIZATION', ''),
    '{{org_name}}': os.environ.get('ORG_NAME', ''),
    '%7B%7Borg_name%7D%7D': os.environ.get('ORG_NAME', '')
}


ignore_dirs = {'.git', '.venv', 'node_modules', 'site', '__pycache__', 'assets'}
ignore_exts = ('.pyc', '.png', '.svg', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot')

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for file in files:
        if file.endswith(ignore_exts) or file == 'bootstrap.sh':
            continue

        filepath = os.path.join(root, file)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            continue

        new_content = content
        for placeholder, replacement in replacements.items():
            new_content = new_content.replace(placeholder, replacement)

        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'[INFO] Updated: {filepath}')

src_dir = os.path.join('.', 'src', 'project_name')
dst_dir = os.path.join('.', 'src', python_pkg)
if os.path.exists(src_dir) and src_dir != dst_dir:
    os.rename(src_dir, dst_dir)
    print(f'[INFO] Renamed directory: {src_dir} -> {dst_dir}')

"

echo "[INFO] Bootstrap complete! You may now delete this script if desired."
