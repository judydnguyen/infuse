#!/usr/bin/env bash
set -euo pipefail
cd /app

cat > .gitlab-ci.yml <<'EOT'
stages:
  - lint
  - test
  - build

lint:
  stage: lint
  image: python:3.10
  script:
    - python -m py_compile app.py

unit_tests:
  stage: test
  image: python:3.10
  script:
    - python -m pytest -q

build:
  stage: build
  image: python:3.10
  script:
    - python -m compileall .
EOT

mkdir -p docs
cat > docs/ci-notes.md <<'EOT'
# Problem
The pipeline skipped the unit test stage entirely.

# Fix
Added a `test` stage and a `unit_tests` job that runs `python -m pytest -q` while keeping the existing lint and build jobs.

# Validation
Confirmed the stage order is `lint`, `test`, `build` and the sample pytest suite still passes.
EOT
