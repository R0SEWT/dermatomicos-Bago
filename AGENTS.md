# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd prime` for full workflow context.
(The detailed beads workflow block below is injected and maintained by `bd init`.)

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some
systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` — use `-o BatchMode=yes` for non-interactive
- `ssh` — use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` — use `-y` flag
- `brew` — use `HOMEBREW_NO_AUTO_UPDATE=1` env var

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

## Session Close (PR flow — supersedes the generic beads protocol in this file)

`main` is protected: a PR is required, and merges are gated on green CI plus resolved
review conversations — with **no approval count** (a solo dev can't self-approve, and
Copilot/Sourcery reviews only ever *Comment*, so they never satisfy a required-approval
rule). **Do not push directly to `main`.**

At session end:
1. Commit work on a **branch**; `git push -u origin <branch>`.
2. Open/update a **PR**; let the configured reviewer (Copilot/Sourcery) run.
3. The merge waits for **green CI + all review conversations resolved** — never `--admin`.
4. Tracking: `bd ready` at start; file follow-up issues at close for the cross-session
   backlog. **TodoWrite is fine for ephemeral, in-session steps.**
5. `bd dolt push` applies only if a dolt remote is configured; otherwise the git-tracked
   `.beads/issues.jsonl` is the sync. `bd remember` and an out-of-repo harness `MEMORY.md`
   don't conflict — use either.

> The generic beads "Session Completion" protocol elsewhere in this file assumes
> trunk-based development (direct push to `main`, `bd dolt push`) and is **superseded**
> by this section.
