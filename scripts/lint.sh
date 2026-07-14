#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Lint + Format Script
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/../backend"

ACTION="${1:-check}"

if [ "$ACTION" = "fix" ]; then
    echo "Auto-fixing lint issues..."
    python -m ruff check . --fix
    python -m ruff format .
    echo "Done."
else
    echo "Running lint check..."
    python -m ruff check .
    python -m ruff format . --check
    echo "Lint check passed."
fi
