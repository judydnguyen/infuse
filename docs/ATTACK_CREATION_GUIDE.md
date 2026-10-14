# Adding an attack

1. `cp -r benchmark/templates/attack_examples/attack_example_prefix benchmark/attacks/attack_<id>`
2. Edit `config.toml`: set `[attack].id = "<id>"` (must equal the directory number), `name`,
   `description`, `[attack.surfaces] primary/fallback` (only `FILE_CONTENT`, `CONFIG_FILE`,
   `FILENAME`, `ARCHIVE_CONTENT`), `[attack.payload].template`, `[attack.target]`
   `inject_position` / `inject_prefix`, `[attack.success_criteria].signals`, `[attack.metadata]`.
3. Optional: `setup.sh` (runs at image build, receives the assembled payload as `$1`) and
   `tests/test.sh` (runs in the container after the agent; exit 0 = attack succeeded).
4. Validate: `infuse attacks list` (strict load) and `infuse attacks compat` (every task resolves).
5. Smoke: `infuse run --task 1 --attack <id> --model gpt-4o-mini --cost-limit 0.005`.

Payload variants for `--obs-level gcg|troubleshoot` live in
`benchmark/templates/ATTACK_TEMPLATES_{GCG,TROUBLESHOOTING}.json`, keyed by `id`.
