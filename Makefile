.PHONY: up down logs build seed neo4j-init train-anomaly-model \
        test-auth test-gateway test-vendor test-risk test-sbom \
        test-compliance test-monitoring test-incident test-shared

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

seed:
	docker compose --profile tools run --rm seed

neo4j-init:
	docker compose --profile tools run --rm neo4j-init

train-anomaly-model:
	docker compose run --rm risk-service python -m app.services.anomaly.train

test-shared:
	docker compose run --rm --no-deps --entrypoint "" auth-service sh -c \
		"pip install -q -e /shared/py-common[test] && python -m pytest /shared/py-common/tests -q"

test-auth:
	docker compose run --rm --no-deps --entrypoint "" auth-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-gateway:
	docker compose run --rm --no-deps --entrypoint "" gateway sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-vendor:
	docker compose run --rm --no-deps --entrypoint "" vendor-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-risk:
	docker compose run --rm --no-deps --entrypoint "" risk-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-sbom:
	docker compose run --rm --no-deps --entrypoint "" sbom-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-compliance:
	docker compose run --rm --no-deps --entrypoint "" compliance-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-monitoring:
	docker compose run --rm --no-deps --entrypoint "" monitoring-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"

test-incident:
	docker compose run --rm --no-deps --entrypoint "" incident-service sh -c \
		"pip install -q -e .[test] && python -m pytest tests -q"
