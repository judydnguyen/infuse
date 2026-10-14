# Runbook — Rebuttal Defense-Grid Expansion

Goal: expand the defense experiment to a **7-model × 7-defense** grid on the
controlled subset, answering reviewers xrpJ-W2 (only 5 models / underpowered)
and xrpJ-W3 / AC-M3 (missing system-level privilege-control defenses).

- **New defense families:** `progent`, `camel` (system-level privilege control,
  added this cycle — see `defenses/runtime/privilege_control.py`).
- **New models:** `gpt-5-nano`, `claude-sonnet-4-6`.
- **Existing 5 models** already have the original 5 defenses; they only need the
  two new defense arms.

The runner **skips trajectories that already exist**, so every command below can
be re-run safely and will only fill missing cells.

---

## 0. Sync code to this machine (do first)

The two new defenses and their vendored references must be present. From the
repo on the run machine:

```bash
git fetch && git checkout rebuttal && git pull
# sanity: these must exist
ls defenses/runtime/privilege_control.py defenses/runtime/command_analysis.py
ls third_party/PROVENANCE.md
python3 -c "from defenses import ProgentDefense, CamelStyleDefense; print('defenses OK')"
```

> If `privilege_control.py` is missing, the branch wasn't pushed — go back to the
> dev machine and `git push` first.

---

## 1. Environment

```bash
cd secured-agent-bench
conda activate <env>            # same env used for main runs
# .env must define:
#   DATA_ROOT_PATH=/tank/judy-shared/agentbench-data   (canonical result store)
#   OPENAI_API_KEY=...          (gpt-5-nano agent + gpt-4o defense-model if used)
#   ANTHROPIC_API_KEY=...       (claude-sonnet-4-6 agent)
# Docker must be running (tasks build images).
```

---

## 2. Fixed experiment parameters (do NOT change — must match existing cells)

```bash
ATTACKS="101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120"
TASKS="9,13,17,3,8,16,27,36,11,25"      # the 10-task controlled subset
ALL_DEFENSES="none,delimiter_isolation,instructional_hardening,input_transform,llama_guard,qwen_guard,progent,camel"
NEW_DEFENSES="progent,camel"
```

Common flags every command uses: `--use-docker --task-prefix`.

---

## 3. Defense-model (policy/judge generator)

The LLM-based arms (`input_transform`, `progent`, `camel`) need a
`--defense-model`. To stay consistent with the **submitted** experiment, use
**Qwen/Qwen3-4B-Instruct-2507 served on vLLM** and point the defense at it:

```bash
# start once, in its own shell / tmux; pick a free port e.g. 8013
vllm serve Qwen/Qwen3-4B-Instruct-2507 --port 8013 --dtype auto
export DEFENSE_VLLM_API_BASE=http://localhost:8013/v1
DEFENSE_MODEL="Qwen/Qwen3-4B-Instruct-2507"
```

> Alternative (simpler, API-only): `DEFENSE_MODEL="gpt-4o"` and **unset**
> `DEFENSE_VLLM_API_BASE`. Acceptable, but note the defense-model then differs
> from the original arms — mention it in the paper if you go this route.

The two guard arms (`llama_guard`, `qwen_guard`) ignore `--defense-model`; they
**auto-start their own vLLM guard servers** on first use:
`meta-llama/Llama-Guard-3-8B` (port 8020) and `Qwen/Qwen3Guard-Gen-8B`. These
need GPU + HuggingFace access to those models.

---

## 4. Batch A — new models (gpt-5-nano, claude-sonnet-4-6), all arms

Skip-logic fills only what's missing (gpt-5-nano already has the 3 prompt/
transform arms; claude has nothing).

```bash
# gpt-5-nano  (OpenAI; no --model-class needed)
./scripts/ablations/defenses/batch_collect_with_defenses.sh \
  "$ATTACKS" "$TASKS" "gpt-5-nano" "$ALL_DEFENSES" \
  --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix

# claude-sonnet-4-6
./scripts/ablations/defenses/batch_collect_with_defenses.sh \
  "$ATTACKS" "$TASKS" "claude-sonnet-4-6" "$ALL_DEFENSES" \
  --model-class anthropic --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix
```

---

## 5. Batch B — existing 5 models, only the two new defenses

Split by serving type.

**5a. API / hosted agents** (`batch_collect_with_defenses.sh`):
```bash
# gpt-4o-mini
./scripts/ablations/defenses/batch_collect_with_defenses.sh \
  "$ATTACKS" "$TASKS" "gpt-4o-mini" "$NEW_DEFENSES" \
  --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix

# gemini-3.1-flash-lite-preview  (litellm gemini/ prefix)
./scripts/ablations/defenses/batch_collect_with_defenses.sh \
  "$ATTACKS" "$TASKS" "gemini/gemini-3.1-flash-lite-preview" "$NEW_DEFENSES" \
  --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix
```

**5b. Open-weight agents** (`batch_collect_with_defenses_openweight.sh`,
`--model-class vllm`). Start each agent's vLLM server first (config in
`configs/models.yaml`), one at a time or on separate GPUs:

```bash
# gemma-3-12b-it   (models.yaml key gemma_3_12b_it, port 8009, tp=2)
vllm serve google/gemma-3-12b-it --port 8009 --tensor-parallel-size 2 --dtype auto &
export VLLM_API_BASE=http://localhost:8009/v1
./scripts/ablations/defenses/batch_collect_with_defenses_openweight.sh \
  "$ATTACKS" "$TASKS" "google/gemma-3-12b-it" "$NEW_DEFENSES" \
  --model-class vllm --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix

# Qwen2.5-14B-Instruct   (models.yaml key qwen_2_5_14b_it)
vllm serve Qwen/Qwen2.5-14B-Instruct --port 8006 --dtype auto &
export VLLM_API_BASE=http://localhost:8006/v1
./scripts/ablations/defenses/batch_collect_with_defenses_openweight.sh \
  "$ATTACKS" "$TASKS" "Qwen/Qwen2.5-14B-Instruct" "$NEW_DEFENSES" \
  --model-class vllm --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix

# Qwen3-4B-Instruct-2507   (models.yaml key qwen_3_4b_it)
vllm serve Qwen/Qwen3-4B-Instruct-2507 --port 8007 --dtype auto &
export VLLM_API_BASE=http://localhost:8007/v1
./scripts/ablations/defenses/batch_collect_with_defenses_openweight.sh \
  "$ATTACKS" "$TASKS" "Qwen/Qwen3-4B-Instruct-2507" "$NEW_DEFENSES" \
  --model-class vllm --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix
```

> If the agent model IS the defense-model (Qwen3-4B case), point
> `DEFENSE_VLLM_API_BASE` at the same server to avoid a second copy.

---

## 6. Smoke test FIRST (recommended before the full fan-out)

Verify `progent`/`camel` behave end-to-end in the real harness on one cell:

```bash
./scripts/ablations/defenses/batch_collect_with_defenses.sh \
  "101" "9" "gpt-5-nano" "progent,camel" \
  --defense-model "$DEFENSE_MODEL" --use-docker --task-prefix
```

Check the resulting `.traj.json` under
`$DATA_ROOT_PATH/results/attack_task/101/9/gpt-5-nano/{progent,camel}/` and
confirm defense events (`progent_block` / `camel_block`) appear when the attack
fires. Then run Batches A and B.

---

## 7. Score & assemble the table

```bash
# rescore ASR-L / ASR-H over the (possibly re-judged) trajectories
python3 scripts/rescore_v2_full.py            # or the current rescore entrypoint
# then per model×defense ASR with CIs for the 7×7 table
```

Report per-defense ASR-L and ASR-H with confidence intervals, and the
security–utility frontier (ASR reduction vs. task-utility loss) so `progent` /
`camel` can be ranked against the observation-level defenses.

---

## 8. Cost / time budget

- Grid delta ≈ **~4,000 new agent runs** (2 new models × up-to-8 arms × 200
  cells, plus 5 models × 2 arms × 100 cells), each a Docker build + agent loop.
- Plan for multiple hours of wall-clock; open-weight agents are GPU-bound and
  should be run one model per GPU.
- `--cost-limit` defaults to `0.005`/run in the script; raise with
  `--cost-limit <usd>` for the larger models if runs get truncated.

---

## Result layout (for reference)

```
$DATA_ROOT_PATH/results/attack_task/<attack>/<task>/<model_slug>/<defense>/*.traj.json
```
`<defense>` ∈ {none, delimiter_isolation, instructional_hardening,
input_transform, llama_guard, qwen_guard, progent, camel}.
