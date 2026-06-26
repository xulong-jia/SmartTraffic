BACKEND_PYTHON := $(shell if [ -x backend/.venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: backend-dev backend-test frontend-dev frontend-build docker-config seed-demo check danger-check

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test:
	cd backend && $(BACKEND_PYTHON) -m pytest tests

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

docker-config:
	docker compose config

seed-demo:
	python3 scripts/seed_demo_data.py

check: backend-test frontend-build docker-config danger-check

danger-check:
	python3 scripts/danger_check.py
