#!/usr/bin/env bash
# A2 — scrub_history: DRY-RUN ONLY git-history secret scrub planner.
# Detects git-filter-repo, builds a replacements file from scripts/leaked_keys.txt,
# dry-runs the rewrite, and PRINTS (does not execute) the destructive force-push.
#
# JSONL emitted on the last line: {"step":"scrub_history","ok":...,"mode":"dry-run","matches":N,"ts":"..."}
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
emit() { printf '{"step":"scrub_history","ok":%s,"mode":"dry-run","matches":%s,"ts":"%s"%s}\n' "$1" "$2" "$TS" "${3:-}"; }

if [ -z "$REPO_ROOT" ]; then
  emit false 0 ',"reason":"not a git repo"'
  exit 2
fi
cd "$REPO_ROOT"

# 1. Require git-filter-repo (do NOT auto-install).
if ! command -v git-filter-repo >/dev/null 2>&1 && ! git filter-repo --help >/dev/null 2>&1; then
  OS="$(uname -s)"
  echo "git-filter-repo not found. Install it manually (NOT auto-installed):" >&2
  case "$OS" in
    Linux)  echo "  pipx install git-filter-repo    # or: sudo apt install git-filter-repo" >&2 ;;
    Darwin) echo "  brew install git-filter-repo" >&2 ;;
    *)      echo "  pip install git-filter-repo     # see https://github.com/newren/git-filter-repo" >&2 ;;
  esac
  emit false 0 ',"reason":"git-filter-repo missing"'
  exit 2
fi

# 2. Ensure leaked-keys source exists (create empty for Igor to populate).
LEAKED="scripts/leaked_keys.txt"
if [ ! -f "$LEAKED" ]; then
  : > "$LEAKED"
  echo "# One leaked secret per line (literal values). Populate, then re-run." >> "$LEAKED"
  echo "Created empty $LEAKED — populate with the leaked literals, then re-run." >&2
fi

# 3. Build git-filter-repo replacements file.
REPL=".git-filter-repo-replacements.txt"
: > "$REPL"
MATCHES=0
while IFS= read -r line; do
  case "$line" in ''|\#*) continue ;; esac
  printf '%s==>REDACTED\n' "$line" >> "$REPL"
  MATCHES=$((MATCHES+1))
done < "$LEAKED"

if [ "$MATCHES" -eq 0 ]; then
  echo "No leaked literals in $LEAKED — nothing to scrub. Populate it first." >&2
  emit false 0 ',"reason":"empty leaked_keys.txt"'
  exit 2
fi

# 4. Dry-run the rewrite (no history modification).
echo "== git filter-repo DRY-RUN ($MATCHES pattern(s)) ==" >&2
git filter-repo --replace-text "$REPL" --dry-run >&2 || true

# 5. Print — DO NOT EXECUTE — the destructive sequence Igor runs manually.
cat >&2 <<'MANUAL'

================ MANUAL, DESTRUCTIVE — run yourself after review ================
# Rewrites ALL history and requires a coordinated force-push. Back up first.
git filter-repo --replace-text .git-filter-repo-replacements.txt --force
git remote add origin git@github.com:Genesis-Conductor-Engine/Yennefer.git  # if dropped by filter-repo
git push --force --all origin
git push --force --tags origin
# Then: rotate the keys (already leaked == already compromised), and have all
# collaborators re-clone (rewritten history breaks existing clones).
=================================================================================
MANUAL

emit true "$MATCHES"
