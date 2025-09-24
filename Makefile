SHELL := /bin/bash

.PHONY: help install server ingest unit test test-light test-headed test-debug lint fmt bench bench-light docker-smoke

help:
	@echo "Targets: install, server, ingest, unit, test, test-light, test-headed, test-debug, lint, fmt, bench, bench-light, docker-smoke"

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt || true
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
	npm ci || npm install
	npx playwright install --with-deps

server:
	./scripts/run_server.sh

ingest:
	PYTHONPATH=. python scripts/ingest.py

unit:
	pytest -q tests/unit

test:
	npm run test:e2e

test-light:
	npm run test:e2e:light

test-headed:
	npm run test:e2e:headed

test-debug:
	npm run test:e2e:debug

lint:
	python -m ruff check app scripts
	python -m black --check app scripts
	python -m isort --check-only app scripts

fmt:
	python -m isort app scripts
	python -m black app scripts
	python -m ruff check --fix app scripts

bench:
	python scripts/bench/bench_rag.py --method hybrid --k 3 --rounds 3 --enable-logs

bench-light:
	./scripts/bench/run_bench.ps1 || true

# Best-effort Docker smoke in bash (Linux/macOS). On Windows use scripts/smoke/app_smoke.ps1
# Requires docker and curl
 docker-smoke:
	docker build -f deploy/docker/Dockerfile -t rag2app:local .
	- docker rm -f rag2app_smoke >/dev/null 2>&1 || true
	docker run -d -p 8000:8000 --name rag2app_smoke rag2app:local
	@echo "Waiting for app health..."; for i in $$(seq 1 30); do if curl -fsS http://127.0.0.1:8000 >/dev/null; then echo OK; break; fi; sleep 0.5; done
	docker rm -f rag2app_smoke >/dev/null 2>&1 || true
