.PHONY: install install-all smoke test lint judge figures compat migrate clean

PY ?= python

install:            ## editable install, core deps only
	pip install -e .
	@test -f .env || cp .env.sample .env
	@echo "Edit .env to add OPENAI_API_KEY (and others as needed)."

install-all:        ## core + analysis + dev + openweight
	pip install -e ".[analysis,dev,openweight]"

smoke:              ## one cheap attacked run (needs OPENAI_API_KEY + Docker)
	infuse run --task 1 --attack 1 --model gpt-4o-mini --cost-limit 0.005

test:               ## unit tests, no API keys or Docker
	$(PY) -m compileall -q infuse
	$(PY) -m pytest tests/

lint:
	ruff check infuse tests scripts

compat:             ## attack x task resolution matrix
	infuse attacks compat

migrate:            ## normalize attack configs and task overlays in place
	infuse migrate-configs --write

judge:              ## judge every trajectory under DATA_ROOT (or --trajectories-dir)
	infuse judge

figures:            ## regenerate paper figures from traj_records.csv
	infuse figures

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
