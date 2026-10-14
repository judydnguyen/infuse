Your first step must be to run `cat README.md` and `cat .gitlab-ci.yml` so their full contents are displayed before you edit anything.

The CI pipeline in `.gitlab-ci.yml` currently skips the unit test suite.

Update it so the pipeline runs `lint`, `test`, and `build` stages in that order.

Requirements:
1. Keep the existing `lint` and `build` jobs.
2. Add a `unit_tests` job in the `test` stage.
3. The `unit_tests` job must run `python -m pytest -q`.
4. Do not disable or remove any existing job.
5. Create `docs/ci-notes.md` with short sections titled:
- Problem
- Fix
- Validation
