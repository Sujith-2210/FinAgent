#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN="${1:---dry-run}"

TARGETS=(
  "$ROOT_DIR/frontend/dist"
  "$ROOT_DIR/frontend/node_modules/.cache"
  "$ROOT_DIR/backend/.pytest_cache"
  "$ROOT_DIR/backend/.hypothesis"
  "$ROOT_DIR/backend/__pycache__"
  "$ROOT_DIR/backend/app/__pycache__"
  "$ROOT_DIR/workspace"
  "$ROOT_DIR/demo_workspace"
)

echo "Workspace cleaner mode: $DRY_RUN"
echo "Project root: $ROOT_DIR"

clean_path() {
  local path="$1"
  if [ ! -e "$path" ]; then
    return 0
  fi

  if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "[DRY-RUN] would remove: $path"
    return 0
  fi

  rm -rf "$path"
  echo "[REMOVED] $path"
}

for target in "${TARGETS[@]}"; do
  clean_path "$target"
done

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "Dry run complete. Re-run with --apply to remove files."
else
  echo "Cleanup complete."
fi
