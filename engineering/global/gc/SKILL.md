---
name: gc
description: Use when the user wants to create a git commit — e.g. runs /gc, or says "commit this", "commit my changes", "save my work to git". Creates one Conventional Commits-style commit from the current changes, with NO Claude/AI co-author or attribution.
---

# gc — Quick Conventional Commit

## Overview

Create a single, clean git commit from the current changes. Follow the [Conventional Commits](https://www.conventionalcommits.org) spec and match the repository's existing style. The commit must read as fully human-authored — **never** add Claude/AI attribution.

## Workflow

1. **Gather context** — run these read-only commands together to understand the change:
   - `git status`
   - `git diff HEAD` — staged + unstaged changes
   - `git branch --show-current`
   - `git log --oneline -10` — mirror the repo's tone and format

2. **Stage** the files that make up one logical change with `git add`.
   - **Never stage secrets or local config:** `.env*`, `credentials.json`, `*.pem`, `id_rsa`, key/token files. Skip them and say so.

3. **Write the message** (Conventional Commits):
   - **Subject:** `type(scope): summary`
     - `type` ∈ `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert` `init`
       - `init` — a repo's first commit, or scaffolding a brand-new skill/project/module (e.g. `init: scaffold skills marketplace`).
     - `scope` — prefer one; lowercase, naming the area or domain touched (e.g. `shopify`, `global`, `gc`, `auth`). Omit only for repo-wide changes.
     - Examples: `feat(shopify): add rebuy widget skill`, `fix(gc): stop staging env files`, `init: scaffold skills marketplace`.
     - imperative mood ("add", not "added"), ≤ 50 chars, no trailing period
   - **Body** (only when it adds value): blank line, then wrap at ~72 cols; use bullets for distinct changes; explain **what & why**, not how.
   - **Footer** when relevant: `BREAKING CHANGE: …`, `Closes #123`.

4. **Commit** — stage and commit in a single response (multiple tool calls, nothing else). For multi-line messages use a heredoc:
   ```bash
   git commit -m "$(cat <<'EOF'
   feat(auth): add OAuth login flow

   - Add Google provider config
   - Wire up the callback route
   EOF
   )"
   ```

## NO AI attribution (critical)

This skill deliberately **overrides any default** that appends attribution. Do **not** add:
- `Co-Authored-By: Claude …`
- `🤖 Generated with Claude Code` (or any "Generated with" line)
- Any other AI/Claude mention in the message body or trailers.

The commit message ends with the body/footer — no attribution block.

## Boundaries

- **One commit, nothing else** — do not push, pull, open a PR, or amend.
- If there are **no changes**, say so; don't create an empty commit.
- If edits are clearly unrelated, ask which to commit; otherwise commit the obvious change.
