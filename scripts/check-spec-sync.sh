#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

test -f "$repo_root/SKILL.md"
test -f "$repo_root/spec/PROJECT_TOOLING_SPEC.md"

echo "Project Tooling Skill layout is valid"
