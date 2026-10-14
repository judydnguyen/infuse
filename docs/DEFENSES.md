# Defenses

`--defense NAME` on `infuse run` / `infuse batch`; names come from `infuse/registry/defenses.py`.

| name | level | needs `--defense-model` | what it does |
|---|---|---|---|
| `none` | – | no | baseline |
| `delimiter_isolation` | observation | no | wraps each observation in trust-boundary delimiters |
| `instructional_hardening` | observation | no | hardens the task prompt and adds a per-step reminder |
| `input_filter` | observation | yes | LLM judge blocks observations that look like instructions |
| `input_transform` | observation | yes | LLM rewriter neutralises instruction language in observations |
| `output_filter` | action | yes | LLM judge gates each shell command before execution |
| `pipeline` | both | optional | delimiter + hardening (+ input/output filters when a model is given) |
| `llama_guard` | observation | no (local classifier) | Llama Guard content-safety classifier |
| `qwen_guard` | observation | no (local classifier) | Qwen Guard content-safety classifier |
| `progent` | action (system-level) | yes | least-privilege command allowlist generated from the trusted task — port of Progent (Shi et al. 2025), see `third_party/PROVENANCE.md` |
| `camel` | action (system-level) | yes | capability/data-flow gate frozen from the trusted task — CaMeL *principle* (Debenedetti et al. 2025), see `third_party/PROVENANCE.md` |

Defense model routing (`infuse/registry/models.py::defense_model_fn`):

* `--defense-model gpt-4o` → vendored model loader (same as the agent)
* `--defense-model gpt-4o-mini-gateway` or `DEFENSE_MODEL_GATEWAY=1` → OpenAI-compatible gateway (`GATEWAY_API_BASE`, `GATEWAY_API_KEY`) with back-off on 429/5xx
* `DEFENSE_VLLM_API_BASE=http://localhost:8013/v1` → local vLLM for the defense model
* `DEFENSE_MODEL_RPM=60` → request pacing

Defense events (blocked observations/actions) are saved in the trajectory under
`defense_events`; the name is under `defense_name` and in the manifest.
