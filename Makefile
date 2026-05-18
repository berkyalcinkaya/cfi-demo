.PHONY: help install db.create db.drop db.reset db.migrate db.ingest db.psql api

PY := .venv/bin/python
PIP := .venv/bin/pip
ALEMBIC := .venv/bin/alembic
DB ?= embpred

help:
	@echo "make install     - create .venv and install Python deps"
	@echo "make db.create   - createdb $(DB)"
	@echo "make db.drop     - dropdb $(DB) (if exists)"
	@echo "make db.reset    - drop, recreate, and migrate $(DB)"
	@echo "make db.migrate  - alembic upgrade head"
	@echo "make db.ingest   - run scripts/ingest.py"
	@echo "make db.psql     - psql $(DB)"
	@echo "make api         - run FastAPI dev server on :8000"

.venv:
	python3 -m venv .venv

install: .venv
	$(PIP) install -e .

db.create:
	createdb $(DB)

db.drop:
	dropdb --if-exists $(DB)

db.reset: db.drop db.create db.migrate

db.migrate:
	$(ALEMBIC) upgrade head

db.ingest:
	$(PY) scripts/ingest.py

db.psql:
	psql $(DB)

api:
	$(PY) -m uvicorn backend.api.main:app --reload --port 8000
