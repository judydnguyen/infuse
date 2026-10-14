# Architecture

## One run, end to end

```
infuse run --task 1 --attack 1 --model gpt-4o-mini
  └─ infuse/cli.py                       parse flags, resolve prefix/overrides
     └─ runners/run_test_task.py      load AttackSpec (benchmark/attacks/attack_1/config.toml)
        │                             model  -> registry/models.agent_model_config
        │                             defense-> registry/defenses.build_defense
        └─ runners/run_single_minisweagent.py
           ├─ injection.assemble_payload(spec, obs_level)     the ONE payload string
           ├─ task setup.sh (gets the payload as $1)
           ├─ envs/test_task_materializer.build_docker_image
           │    ├─ docker build  (task Dockerfile, environment/app copied in)
           │    └─ injection.inject(spec, TaskSurfaces, build_ctx, strategy)
           │         resolve() -> select() -> handlers[surface]()  -> InjectionRecord
           │         docker cp patched files -> docker commit
           ├─ runners/task_runner.run_task
           │    ├─ envs/surface_tracking.SurfaceTrackingWrapper (observed surfaces per command)
           │    ├─ agents/minisweagent DefaultAgent  (+ defense hooks)
           │    ├─ evaluate_task: attacks/attack_<id>/tests/test.sh, task tests/test.sh
           │    └─ save_traj -> <results>/attack_task/<attack>/<task>/<model>/<i>_task_<id>.traj.json
           └─ runners/manifest.write_manifest -> ...<i>_task_<id>.manifest.json
```

## Post-hoc

```
infuse judge    judge/batch_llm_judge.py   per-trajectory *.eval.json (ASR + completion, V2 rubric via judge/rescore_v2.py)
infuse records  analysis/records.py        traj_records.csv / benign_records.csv
infuse figures  analysis/figures.py        figs/*.pdf|png
```

## Where things are decided

| Concern | Module | Nothing else may |
|---|---|---|
| filesystem locations | `infuse/paths.py` | build paths from `__file__` or hardcode machines |
| surface names | `infuse/surfaces.py` | define another enum/alias table |
| attack/task schema | `infuse/injection/spec.py` | read `config.toml` / `benign.toml` directly |
| payload bytes | `infuse/injection/assemble.py` | concatenate prefix + template |
| injection target | `infuse/injection/resolver.py` | pick files |
| writing payloads | `infuse/injection/handlers/` | touch the build context |
| defense names | `infuse/registry/defenses.py` | `if name == ...` |
| model names/classes | `infuse/registry/models.py` + `benchmark/configs/models.yaml` | alias tables |
| results layout | `infuse/paths.py` (`attack_results_dir`, `benign_results_dir`) | compute paths in shell |

## Results layout (unchanged from the legacy repo)

```
<DATA_ROOT>/
  attack_task/<attack_id>/<task_id>/<model>/<i>_task_<id>.traj.json      + .manifest.json + .eval.json
  benign_task/<model>/task_<id>/<i>_task_<id>.traj.json
  batch_logs/batch_<timestamp>.jsonl
  traj_records.csv, benign_records.csv
```
