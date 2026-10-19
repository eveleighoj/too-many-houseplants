#!/usr/bin/env bash
# Checks that every commit in BASE..HEAD is a strict Conventional Commit: no merge commits
# (rebase instead) and no leftover fixup!/squash! commits. CI runs this on every PR.
#
#   scripts/check-commits.sh                      # your branch vs origin/main
#   scripts/check-commits.sh <base> <head>
#
# Needs uv. Keep the version in step with .pre-commit-config.yaml.
set -euo pipefail

base="${1:-origin/main}"
head="${2:-HEAD}"
checker=(uvx --quiet --from conventional-pre-commit==4.4.0 conventional-pre-commit --strict)

message_file="$(mktemp)"
trap 'rm -f "$message_file"' EXIT

failed=0
checked=0
for sha in $(git rev-list --reverse "$base..$head"); do
  checked=$((checked + 1))
  git log -1 --format=%B "$sha" > "$message_file"
  if "${checker[@]}" --no-color "$message_file" > /dev/null 2>&1; then
    echo "✓ $(git log -1 --format='%h %s' "$sha")"
  else
    echo "✗ $(git log -1 --format='%h %s' "$sha")"
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  cat <<'HELP'

Some commits aren't Conventional Commits (https://www.conventionalcommits.org), e.g.
  feat(trips): add stays     fix: handle empty trips     docs: explain seeding
Merge commits aren't allowed either: update your branch with `git rebase origin/main`.
Reword commits with `git rebase -i origin/main` (mark them `reword`), then
`git push --force-with-lease`.
HELP
  exit 1
fi
echo "All $checked commit(s) are Conventional Commits."
