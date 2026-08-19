.PHONY: install test run docker-up smoke
install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

run:
	uvicorn code_assistant.api:app --reload

docker-up:
	docker compose up --build

smoke:
	python -m code_assistant.cli --workspace .tmp-assistant index tests/fixture
