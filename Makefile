PYTHON ?= python3
VENV_PY = .venv/bin/python
export PYTHONPATH := backend

.PHONY: setup build run dev-api dev-ui seed reset test evaluate model reindex
setup:
	$(PYTHON) -m venv .venv
	test -f .env || cp .env.example .env
	$(VENV_PY) -m pip install -r backend/requirements.txt
	npm --prefix frontend ci
	$(MAKE) seed build
build:
	npm --prefix frontend run build
run:
	$(VENV_PY) -m uvicorn navylink.main:app --host 127.0.0.1 --port 8000 --env-file .env
dev-api:
	$(VENV_PY) -m uvicorn navylink.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
dev-ui:
	npm --prefix frontend run dev
seed:
	$(VENV_PY) -m navylink.seed
reset:
	$(VENV_PY) -m navylink.seed --reset
test:
	$(VENV_PY) -m pytest backend/tests -q
	$(MAKE) build
evaluate:
	$(VENV_PY) -m navylink.evaluate
model:
	$(VENV_PY) -m pip install -r backend/requirements-semantic.txt
	$(VENV_PY) -m navylink.prepare_model
reindex:
	$(VENV_PY) -m navylink.reindex
