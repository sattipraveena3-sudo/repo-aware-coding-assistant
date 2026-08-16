.PHONY: install test run docker-up smoke
install:
	python -m pip install -r requirements.txt

test:
	pytest -q

run:
	uvicorn app:app --reload

docker-up:
	docker compose up --build

smoke:
	python -m code_assistant.cli --workspace .tmp-assistant index tests/fixture
