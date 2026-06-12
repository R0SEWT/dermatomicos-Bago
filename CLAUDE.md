# dermatomicos-Bago — AI Agent Instructions

## Domain / Scientific Context

Proyecto de hackathon (Laboratorios Bagó, dermatología pediátrica — "Hackaton Bago Grupo 7").
Mide la **carga nocturna de eccema atópico (dermatitis atópica)** en bebés mediante **audio
pasivo**: un celular junto a la cuna escucha la noche y cuantifica llanto y rascado, los dos
proxies acústicos del prurito/brote que hoy se reportan de memoria y subjetivamente.

- **Problem**: el seguimiento del eccema infantil depende de reportes subjetivos de los padres
  (¿lloró?, ¿se rascó mucho?). No hay una medida objetiva, densa y continua de la carga nocturna.
- **Outcome / target**: una señal **objetiva** por noche — segundos/episodios de llanto y rascado,
  despertares, fragmentación del sueño — agregada en un **estado de severidad** que reacciona en
  vivo y dispara un aviso de "escalada de brote → regístralo para tu consulta", más un reporte
  para el dermatólogo. Posicionamiento del demo: **vender objetividad/densidad de señal; insinuar
  lead-time, sin afirmar predicción longitudinal** (no hay datos de cohorte en el escenario).
- **Data provenance**:
  - **Llanto** — zero-shot con YAMNet (modelo público entrenado en Google AudioSet); usa sus
    clases de fábrica "Baby cry, infant cry" y "Crying, sobbing". Sin datos propios ni entrenamiento.
  - **Rascado** — YAMNet no tiene clase limpia → **dataset propio scrappy** grabado por el equipo
    (`scripts/record_dataset.py`): clips `positive`/`negative` cerca del mic, transfer learning con
    un MLP sobre embeddings 1024-D de YAMNet.
  - **Severidad** — instancia mínima del framework **EczemaPred** (citado, NO replicado): acumulador
    con decay sobre la carga acústica. No hay validación de cohorte; es honesto en el pitch.

## Architecture

Pipeline de streaming de audio. Flujo de una ventana de ~1s:

```
mic (16k mono) ─▶ YAMNet.infer ─▶ scores[521] + embedding[1024]
                                      │              │
                            cry_score(scores)   ScratchHead.predict_proba(emb)
                                      └──────┬───────┘
                                    classify_frame → {cry, scratch, quiet, other}
                                             │
                          StreamDetector.run_live(on_event)  ◀── API para la UI
                                             │
              frames_to_episodes ─▶ aggregate ─▶ NightFeatures
                                             │
                          SeverityTracker.update ─▶ ReportBuilder.build → data/gold/reports/
```

```bash
# entrenar la cabeza de rascado (tras grabar el dataset)
uv run python scripts/record_dataset.py positive 15   # y negative
# extraer embeddings → data/silver, entrenar → models/scratch_head.joblib (ver plan)
# demo en vivo (necesita micrófono — corre en laptop, no en el server gorgo)
uv run derma live 30
```

**Contrato para la UI** (la UI se construye aparte, NO en este repo): consume
`StreamDetector.run_live(on_event)` (stream de `Event`), `SeverityTracker.value/.history`,
y `ReportBuilder.build(features, tracker) -> str` markdown.

**GPU**: `uv sync --extra gpu` en máquina NVIDIA (p.ej. host `gorgo`); laptop CPU-only usa `uv sync`.

## Key Files

| File | Purpose |
|------|---------|
| `src/dermatomicos_bago/config.py` | Umbrales y pesos (DetectConfig, SeverityConfig, FeatureConfig) — única fuente de verdad |
| `src/dermatomicos_bago/models/yamnet.py` | Wrapper YAMNet: carga hub, class_map, `infer(waveform)→(scores, embedding)` |
| `src/dermatomicos_bago/models/labels.py` | Resuelve clases cry por nombre + `classify_frame` (puro) |
| `src/dermatomicos_bago/models/scratch.py` | `embed_clips` + `ScratchHead` (MLP sklearn sobre embeddings) |
| `src/dermatomicos_bago/audio/{capture,windowing}.py` | Mic/WAV 16k + framing por ventana deslizante |
| `src/dermatomicos_bago/pipeline/detector.py` | `StreamDetector` — orquesta cry + scratch en vivo |
| `src/dermatomicos_bago/pipeline/{events,features,severity,report}.py` | Episodios, features por noche, severidad, reporte (todos puros) |
| `src/dermatomicos_bago/cli.py` | `derma live` — end-to-end mic → noche → severidad → reporte |
| `scripts/record_dataset.py` | Graba clips etiquetados de rascado a `data/bronze/scratch/` |

## Data Conventions

Medallion adaptado al dominio acústico (todo bajo `data/`, gitignored):

- **bronze** → audio crudo: `data/bronze/scratch/{positive,negative}/*.wav`, sesiones grabadas.
- **silver** → embeddings extraídos: `data/silver/scratch_embeddings.parquet` (1024-D + label).
- **gold** → analítico: `data/gold/nights/*.parquet` (features por noche), `data/gold/reports/*.md`.
- `models/scratch_head.joblib` vive fuera de `data/` (artefacto entrenado).
- **Polars over pandas**; numpy solo donde una librería lo exige (YAMNet, sklearn).
- DuckDB disponible para joins SQL sobre los parquet de gold si hace falta.

## Conventions

- **Audio**: siempre 16 kHz mono float32 en `[-1, 1]` (lo que espera YAMNet). `load_wav_16k`
  resamplea cualquier WAV de entrada.
- **Clases de YAMNet por nombre, nunca por índice** — el orden de las 521 clases no se hardcodea
  (`resolve_class_indices` busca por `display_name`).
- **Determinismo**: `ScratchHead` usa `random_state=0`. La lógica pura (windowing, labels, events,
  features, severity, report) no toca modelo ni mic y se testea sin `-m slow`.
- **`setuptools<81` está pineado**: `tensorflow_hub` importa `pkg_resources`, removido en setuptools 82.
- Tests que descargan el modelo o usan hardware van marcados `@pytest.mark.slow`.


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
