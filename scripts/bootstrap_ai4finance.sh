#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$ROOT_DIR/external/ai4finance"

mkdir -p "$TARGET_DIR"

clone_if_missing() {
  local repo_url="$1"
  local repo_name="$2"
  local destination="$TARGET_DIR/$repo_name"

  if [ -d "$destination/.git" ]; then
    echo "✅ $repo_name already cloned at $destination"
    return 0
  fi

  echo "📦 Cloning $repo_name..."
  git clone --depth 1 "$repo_url" "$destination"
}

clone_if_missing "https://github.com/AI4Finance-Foundation/FinGPT.git" "FinGPT"
clone_if_missing "https://github.com/AI4Finance-Foundation/FinRAG.git" "FinRAG"
clone_if_missing "https://github.com/AI4Finance-Foundation/FinRobot.git" "FinRobot"
clone_if_missing "https://github.com/AI4Finance-Foundation/FinRL.git" "FinRL"

COMMUNITY_TARGET_DIR="$ROOT_DIR/external/community"
mkdir -p "$COMMUNITY_TARGET_DIR"
if [ -d "$COMMUNITY_TARGET_DIR/finance-agent/.git" ]; then
  echo "✅ finance-agent already cloned at $COMMUNITY_TARGET_DIR/finance-agent"
else
  echo "📦 Cloning finance-agent..."
  git clone --depth 1 "https://github.com/kamathhrishi/finance-agent.git" "$COMMUNITY_TARGET_DIR/finance-agent"
fi

echo "🎉 AI4Finance repositories are ready in $TARGET_DIR"
