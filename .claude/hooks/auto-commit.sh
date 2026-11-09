#!/usr/bin/env bash
# Stop hook: when Claude finishes a reply, commit any changed files and push to GitHub.
# Files ending in Hello.py are skipped; the user commits those by hand.

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
SKIP=':(exclude)*Hello.py'
msg=""

git add -A -- . "$SKIP"
if ! git diff --cached --quiet -- . "$SKIP"; then
  files=$(git diff --cached --name-only -- . "$SKIP" | head -5 | paste -sd' ' -)
  if git commit -q -m "Auto-commit: update $files" \
       -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- . "$SKIP"; then
    msg="Auto-committed: $files"
  fi
fi

# Push whenever the branch has commits that GitHub doesn't have yet.
if git rev-parse -q --verify '@{u}' >/dev/null && [ -n "$(git log '@{u}..' --oneline)" ]; then
  if git push -q; then
    msg="${msg:+$msg, }pushed to GitHub"
  else
    msg="${msg:+$msg, }push FAILED (run git push to see why)"
  fi
fi

[ -n "$msg" ] && printf '{"systemMessage": "%s"}\n' "$msg"
exit 0
