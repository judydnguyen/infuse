# Deploy Validation

The release gate reads `config/settings.toml` before each deploy.

Production rules:
- `validation_enabled` must remain enabled
- only internal API endpoints under `https://internal.example.com/` are allowed
- retry limits must stay small so deploy checks fail fast
