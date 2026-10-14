# Reproducing the paper

## From released trajectories (no agent runs, ~1 h, judge cost only)

```bash
make install
bash scripts/download_artifacts.sh            # trajectories -> $DATA_ROOT_PATH (or ./results)
infuse judge --skip-existing                     # only trajectories without an eval file
infuse records && infuse records --benign           # traj_records.csv, benign_records.csv
infuse figures --out-dir figs
```

## From scratch

| experiment (`benchmark/experiments/`) | cells | what it feeds |
|---|---|---|
| `main_grid` | 56 attacks × 40 tasks × models | ASR / utility tables, model panel figure |
| `benign` | 40 tasks × models | utility baseline |
| `defense_grid` | 20 attacks × 10 tasks × 8 defenses × models | defense comparison |
| `multi_surface` | 56 × 40 × models, `surfaces_mode=multi` | multi-surface ablation |

```bash
infuse batch --experiment main_grid   --models gpt-4o-mini,claude-haiku-4-5 --jobs 2
infuse batch --experiment benign      --models gpt-4o-mini,claude-haiku-4-5
infuse batch --experiment defense_grid --models gpt-4o-mini --defense-model gpt-4o
infuse batch --experiment multi_surface --models gpt-4o-mini
```

Every command is resumable: cells with an existing trajectory are skipped
unless `--overwrite`. `--dry-run` prints the cell list. Costs: one cell is capped
by `--cost-limit` (default 0.005 USD for cheap models, see `models.yaml`); the
main grid for one model is 2,240 cells.

Open-weight models: `infuse serve-vllm <key>` in one shell, then the same `infuse batch`
commands with `--models <key>`.

## Reproducibility notes

* `--strategy task_order` (default) selects injection targets exactly as the
  legacy pipeline did; do not change it when extending an existing grid.
* Each run's `*.manifest.json` records git SHA, model, defense, payload hash,
  selected surface/file and Docker image — compare these before merging result sets.
* Attack configs 31–35 had wrong ids until 2026-10-05 (see `docs/INJECTION.md`).
