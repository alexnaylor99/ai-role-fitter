PY := .venv/bin/python
PROVIDER ?= mock
PORT ?= 8000

.PHONY: setup dev test lint fmt secrets check eval sample

setup:  ## Create the virtualenv, install deps and git hooks
	python3.12 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements-dev.txt
	.venv/bin/pre-commit install
	@test -f .env || echo "No .env yet: copy .env.example to .env and add your keys (main folder only, never in a worktree)."

dev:  ## Run the app on http://127.0.0.1:$(PORT) (local only); make dev PORT=8001
	$(PY) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT) --reload

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

fmt:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

secrets:  ## Scan tracked files for secrets against the baseline
	git ls-files -z | xargs -0 .venv/bin/detect-secrets-hook --baseline .secrets.baseline

check: lint test secrets  ## Everything CI runs (except gitleaks)

eval:  ## Score the eval personas: make eval PROVIDER=claude|ollama|mock
	$(PY) -m tests.eval --provider $(PROVIDER)

sample:  ## Regenerate samples/sample_report.json: make sample PROVIDER=claude
	$(PY) -m scripts.build_sample_report --provider $(PROVIDER)
