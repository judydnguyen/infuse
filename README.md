<div align="center">

# INFUSE

### A Unified Surface Benchmark for Indirect Prompt Injection in Agentic Systems

[![arXiv](https://img.shields.io/badge/arXiv-2610.20776-b31b1b.svg)](https://arxiv.org/abs/2610.20776)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-4%2C858%20passing-brightgreen)](tests/)
[![Tasks](https://img.shields.io/badge/tasks-40-blue)](benchmark/tasks/)
[![Attacks](https://img.shields.io/badge/attacks-56-red)](benchmark/attacks/)
[![Defenses](https://img.shields.io/badge/defenses-11-orange)](docs/DEFENSES.md)

**Plant an instruction in the files a coding agent will read. Measure whether it obeys, and whether it still finishes the job.**

[Install](#-install) · [Quick start](#-quick-start) · [Grids](#-grids) · [Evaluate](#-evaluate--reproduce) · [How it works](#-how-injection-works) · [Results](#-results) · [Docs](#-documentation)

<img src="assets/overview.png" alt="INFUSE overview: an agent with shell, code, package, network and git tools works in a task environment; an adversary plants a payload from one of five threat categories into an injection surface (here, a comment in train.py) and the agent exfiltrates a private SSH key" width="100%">

</div>

---

## ✨ What INFUSE does

An agent built on [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) solves a real
filesystem or coding task inside Docker. Before it starts, INFUSE plants an adversarial
instruction somewhere the agent will look: inside a source or config file, as a file name, or
inside an archive. Two numbers come out of every run:

| metric | question it answers |
|:--|:--|
| **ASR** (attack success rate) | Did the agent follow the planted instruction? Scored by an LLM judge and a heuristic verifier. |
| **Utility** | Did the agent still complete the original task? Scored by the task's hidden `tests/test.sh`. |

Every trajectory is paired with a `*.manifest.json` that records the exact payload bytes,
the file they went into, the resolution strategy, the model, the defense, and the git SHA.

<details>
<summary><b>At a glance</b></summary>

| | |
|:--|:--|
| **Tasks** | 40 self-contained tasks, each with a Dockerfile, an instruction, and hidden tests — `benchmark/tasks/` |
| **Attacks** | 56 attacks, one `config.toml` each — `benchmark/attacks/` |
| **Surfaces** | `FILE_CONTENT` · `CONFIG_FILE` · `FILENAME` · `ARCHIVE_CONTENT` |
| **Defenses** | 11, from delimiter isolation to Progent- and CaMeL-style privilege control — `docs/DEFENSES.md` |
| **Models** | any LiteLLM provider (OpenAI, Anthropic, Gemini, …) or a local vLLM server |
| **Entry point** | one CLI: `infuse` |

</details>

---

## 📦 Install

```bash
git clone <this repo> infuse && cd infuse
conda env create -f environment.yml && conda activate infuse   # or: pip install -e ".[analysis,dev]"
make install            # editable install, copies .env.sample → .env
$EDITOR .env            # OPENAI_API_KEY=…  (ANTHROPIC_API_KEY, GEMINI_API_KEY optional)
make test               # 4,858 tests · no API keys · no Docker
```

> **Requirements.** Docker must be running for `infuse run` / `infuse batch` (each task builds its
> own image). Results go to `./results/` unless `DATA_ROOT_PATH` is set in `.env`.

---

## 🚀 Quick start

```bash
# one attacked run (≈ $0.005)
infuse run --task 1 --attack 1 --model gpt-4o-mini --cost-limit 0.005   # task prefix on by default; --no-task-prefix to disable

# benign baseline for utility
infuse run --task 1 --model gpt-4o-mini

# with a defense
infuse run --task 5 --attack 120 --model claude-haiku-4-5 --defense delimiter_isolation
infuse run --task 5 --attack 120 --model gpt-4o-mini --defense progent --defense-model gpt-4o
```

Each run prints a JSON summary on stdout and writes two files:

```
results/attack_task/<attack>/<task>/<model>/
├── task_1_37fdd2d5_attack1.traj.json       # full agent trajectory + evaluation
└── task_1_37fdd2d5_attack1.manifest.json   # what was injected, where, by which strategy
```

<details>
<summary><b>Example manifest excerpt</b></summary>

```json
{
  "task_id": "task_1", "attack_id": "1", "model": "gpt-4o-mini", "defense": "none",
  "resolution_strategy": "task_order", "docker_image": "task_zip_extraction:1.0",
  "injection": {
    "mode": "single", "position": "append",
    "payload_sha256": "11902177a69a…",
    "candidates": [{"surface": "FILE_CONTENT", "path": "extract.py"},
                   {"surface": "FILENAME",     "path": "extract.py"}],
    "selected":   [{"surface": "FILE_CONTENT", "target": "extract.py", "written": "extract.py"}]
  },
  "verifier_baseline": {"script": "solution.sh", "passed": true},
  "outcome": {"exit_status": "LimitsExceeded", "cost_usd": 0.0041, "n_steps": 21}
}
```

</details>

---

## 🧮 Grids

```bash
infuse batch --attacks 1-10 --tasks 1-5 --models gpt-4o-mini,gpt-5-nano     # ad-hoc grid
infuse batch --experiment main_grid --models gpt-4o-mini --jobs 2            # saved grid
infuse batch --experiment defense_grid --defense-model gpt-4o --dry-run      # list cells, run nothing
```

* **Resumable.** A cell with an existing trajectory is skipped unless `--overwrite`.
* **Declarative.** Saved grids live in `benchmark/experiments/`; any CLI flag overrides the YAML.
* **Logged.** Every batch appends one JSON line per cell to `<results>/batch_logs/`.

| experiment | cells per model | feeds |
|:--|--:|:--|
| `main_grid` | 56 × 40 = 2,240 | ASR / utility tables, model panel figure |
| `benign` | 40 | utility baseline |
| `defense_grid` | 20 × 10 × 8 = 1,600 | defense comparison |
| `multi_surface` | 2,240 | multi-surface ablation |

<details>
<summary><b>Open-weight models via vLLM</b></summary>

```bash
CUDA_VISIBLE_DEVICES=0 infuse serve-vllm llama_3_1_8b      # keys live in benchmark/configs/models.yaml
infuse batch --experiment main_grid --models llama_3_1_8b
```

Add a model by appending an entry (`model_id`, `revision`, `port`, `tensor_parallel_size`, …) to
`benchmark/configs/models.yaml`. API models need no entry.

</details>

---

## 📊 Evaluate & reproduce

```bash
infuse judge                     # LLM judge over every trajectory (ASR + task completion)
infuse records                   # aggregate trajectories + judge output → traj_records.csv
infuse figures --out-dir figs    # figures from the records
```

`docs/REPRODUCE.md` maps each experiment to the figures it feeds and gives cost estimates.
Released trajectories: `scripts/download_artifacts.sh`.

---

## 🔍 Inspect the benchmark

```bash
infuse attacks list        # id · name · surfaces · position
infuse attacks compat      # which surface each attack × task pair injects into
infuse tasks list          # surfaces each task declares
infuse migrate-configs     # validate and normalise configs (dry run; --write applies)
```

<details>
<summary><b>Sample <code>infuse attacks compat</code> output</b></summary>

```
attack × task resolution (task_order): 56 attacks × 40 tasks, 0 pair(s) with no injection target
        1   2   3   4   5   6   7   8   9  10  11  12  13  14 …
    1   F   F   F   F   F   F   F   N   F   N   F   F   F   N
    2   F   F   F   F   F   F   F   N   F   N   F   F   F   N
  …
legend: F=FILE_CONTENT  C=CONFIG_FILE  N=FILENAME  A=ARCHIVE_CONTENT  .=none
```

</details>

---

## ⚙️ How injection works

```
 benchmark/attacks/attack_<id>/config.toml ─┐
                                            ├─▶ AttackSpec, TaskSurfaces   strict schema, fails loudly
 benchmark/tasks/task_<id>/…/benign.toml  ─┘            │
                                                        ▼
                                             resolve(strategy)   task_order │ attack_preference
                                                        │
                                                        ▼
                                             select(mode)        single │ multi (≤ 3 surfaces)
                                                        │
                                                        ▼
                                             handlers[surface]   FILE_CONTENT · CONFIG_FILE · FILENAME · ARCHIVE_CONTENT
                                                        │
                                                        ▼
                                           docker cp → docker commit → InjectionRecord → manifest
```

| guarantee | how it is enforced |
|:--|:--|
| the payload bytes are identical in the file, in `setup.sh`'s argument, and in the manifest | one function, `assemble_payload`, hashed with SHA-256 |
| `task_order` reproduces every trajectory collected so far | `tests/test_resolver_equivalence.py` compares against the legacy injector for all 4,480 attack × task × mode cases |
| no attack × task pair silently has nothing to inject into | `tests/test_cli.py::test_compat_matrix_every_pair_resolves` |
| a verifier that fires on the payload alone is flagged | `infuse run` executes each attack's verifier on the untouched image first and stores `verifier_baseline`; read `test_sh.informative`, not `test_sh.passed` |

Full detail, including the two resolution strategies and the surface vocabulary: `docs/INJECTION.md`.

---

## 🗂 Layout

```
infuse/                     the package
├── cli.py                  `infuse` entry point
├── paths.py                every filesystem location, in one place
├── surfaces.py             the surface vocabulary
├── injection/              spec · resolver · assembler · handlers · injector · migrate
├── registry/               defenses · models
├── runners/                run_test_task · batch · manifest · verifier
├── envs/                   Docker / Daytona / local, materializer, surface tracking
├── defenses/               11 defenses
├── evaluators/             script evaluator, LLM-judge rubric
├── judge/                  batch judge, V2 rescoring
├── analysis/               records · summary · figures
└── agents/                 vendored mini-swe-agent

benchmark/                  the data
├── tasks/task_<id>/        Dockerfile · instruction.md · tests/test.sh · environment/overlays/benign.toml
├── attacks/attack_<id>/    config.toml (+ setup.sh, tests/test.sh)
├── configs/                models.yaml · task_inject_prefixes.json
├── experiments/            main_grid · benign · defense_grid · multi_surface
└── templates/              payload variants (gcg, troubleshoot), legacy eval scripts

docs/  tests/  third_party/ (vendored Progent & CaMeL cores, see PROVENANCE.md)
```

---

## 📚 Documentation

| document | contents |
|:--|:--|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | end-to-end call trace, where each decision lives, results layout |
| [`docs/INJECTION.md`](docs/INJECTION.md) | surfaces, resolution strategies, payload assembly, manifest, known data fixes |
| [`docs/DEFENSES.md`](docs/DEFENSES.md) | the 11 defenses, which need a model, routing options |
| [`docs/REPRODUCE.md`](docs/REPRODUCE.md) | experiments → figures, cost and time estimates |
| [`docs/TASK_CREATION_GUIDE.md`](docs/TASK_CREATION_GUIDE.md) | adding a task |
| [`docs/ATTACK_CREATION_GUIDE.md`](docs/ATTACK_CREATION_GUIDE.md) | adding an attack |

---

## 📈 Results

Figures from the arXiv preprint. 19 LLMs, 41,824 adversarial trajectories, 720 benign reference runs.

<p align="center">
<img src="assets/headline_asr_utility.png" alt="ASR-L and Utility-L drop for six selected models" width="60%">
</p>

**Attack success and utility drop.** ASR-L (%) and Utility-L drop for six selected models, ordered by
increasing ASR-L. Utility drop is benign minus attacked utility in percentage points; negative
values mean utility went up under attack. Sonnet 4.6's low ASR-L comes from runs cut short by a
binding cost cap, so it shouldn't be read as robustness.

<img src="assets/capability_corr_grid.png" alt="Per-model ASR-L against MMLU-Pro, benign trajectory length and reasoning tokens" width="100%">

**Capability is not robustness.** Per-model ASR-L plotted against MMLU-Pro accuracy (left), mean
benign trajectory length (middle), and mean reasoning-token volume (right). Lines are OLS fits
with 95% confidence bands.

<img src="assets/taskwise_heatmap.png" alt="Task by threat-category heatmap of ASR-L" width="100%">

**Where attacks land.** ASR-L for each task × threat category, attacks 101–120, no defense, pooled
over the 14 models evaluated on these attacks.

<img src="assets/defense_per_model.png" alt="Per-model ASR-L under each defense" width="100%">

**Defenses.** Per-model ASR-L under each evaluated defense; the no-defense baseline is in grey.
Instructional hardening lowers mean attack success from 58.2% to 14.3%, but how much
each defense helps depends on the model.

---

## 📄 Paper

*INFUSE: A Unified Surface Benchmark for Indirect Prompt Injection in Agentic Systems*,
Thuy Dung Nguyen, Jingyi Guo, Rana Seda Dubauskas, Sreepriya Damuluru, Taylor T. Johnson, and
Kevin Leach (Vanderbilt University). [arXiv:2610.20776](https://arxiv.org/abs/2610.20776), 2026.

## 📝 Citation

```bibtex
@article{nguyen2026infuse,
  title   = {{INFUSE}: A Unified Surface Benchmark for Indirect Prompt Injection in Agentic Systems},
  author  = {Nguyen, Thuy Dung and Guo, Jingyi and Dubauskas, Rana Seda and Damuluru, Sreepriya and Johnson, Taylor T. and Leach, Kevin},
  journal = {arXiv preprint arXiv:2610.20776},
  year    = {2026},
  eprint  = {2610.20776},
  archivePrefix = {arXiv},
  doi     = {10.48550/arXiv.2610.20776},
  url     = {https://arxiv.org/abs/2610.20776}
}
```

See also [`CITATION.cff`](CITATION.cff).

<div align="center">
<sub>INFUSE is released under the MIT license. Vendored third-party components keep their original licenses; see <code>third_party/PROVENANCE.md</code>.</sub>
</div>
