.PHONY: setup test run build-frontend docker-build docker-up clean

PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest
UVICORN := .venv/bin/uvicorn

setup:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

test:
	$(PYTEST) tests/ -v

test-fast:
	$(PYTEST) tests/test_api_e2e.py -v

build-frontend:
	cd frontend && npm run build

run: build-frontend
	$(UVICORN) api.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t fraudshield/realtime-fraud-platform:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__ frontend/dist frontend/node_modules
