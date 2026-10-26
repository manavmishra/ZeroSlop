#!/usr/bin/env bash
# Keep release comparisons usable after a force-push removes the old commit.
set -euo pipefail

if [ "${EVENT_NAME:-}" = "pull_request" ]; then
  : "${BASE_REF:?A pull request must identify its base branch}"
  git fetch --no-tags origin "$BASE_REF" >&2
  printf 'origin/%s\n' "$BASE_REF"
elif [[ "${BEFORE:-}" =~ ^[[:xdigit:]]{40}$ ]] &&
     git cat-file -e "$BEFORE^{commit}" 2>/dev/null &&
     git merge-base --is-ancestor "$BEFORE" HEAD; then
  printf '%s\n' "$BEFORE"
else
  echo "Push base unavailable or unreachable; using the merge-base with origin/main" >&2
  git fetch --no-tags origin main >&2
  base="$(git merge-base HEAD origin/main)"
  if [ "$base" = "$(git rev-parse HEAD)" ]; then
    # A main push has already moved origin/main to HEAD. Compare its parent
    # rather than silently treating released changes as an empty delta.
    echo "origin/main already points at HEAD; checking its first-parent delta" >&2
    base="$(git rev-parse --verify HEAD^1)"
  fi
  printf '%s\n' "$base"
fi
