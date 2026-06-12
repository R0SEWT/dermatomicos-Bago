# dermatomicos-Bago — AI Agent Instructions

## Domain / Scientific Context

<!-- The real-world problem this project addresses. State the claim/objective, the outcome,
     and — critically — the data provenance (own data? regional/Peruvian domain? public source?).
     This is the differentiator; be concrete. -->

- **Problem**: <!-- fill -->
- **Outcome / target**: <!-- fill -->
- **Data provenance**: <!-- fill: source, ownership, how acquired -->

## Architecture

<!-- How the project runs. If it's a pipeline, describe the stages and the data flow between them. -->

```bash
# e.g. uv run ingest && uv run features && uv run model
```

## Key Files

| File | Purpose |
|------|---------|
| `src/dermatomicos_bago/...` | <!-- fill --> |
| `configs/...` | <!-- fill --> |

## Data Conventions

<!-- Adjust/remove if this is not a data project. Defaults reflect the medallion + polars/duckdb stack. -->

- **Layers**: raw → `data/bronze/`, cleaned → `data/silver/`, analytic → `data/gold/`. All gitignored.
- **Polars over pandas** everywhere; only drop to numpy when a library requires it.
- **DuckDB for SQL joins** across parquet; Polars for local transforms.
- **Remote silver**: reference the remote root via `$SILVER` in SQL when pulling shared data.
- Keep dates as typed `Date`, never strings, in intermediate tables.

## Conventions

<!-- Project-specific rules: ID normalization, seeds, temporal discipline, naming, etc. -->


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
