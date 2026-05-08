.PHONY: install generate db migrate seed setup dev test

install:
	pip install -r requirements.txt

generate:
	datamodel-codegen \
		--input api/openapi.yaml \
		--input-file-type openapi \
		--output models/schemas.py \
		--output-model-type pydantic_v2.BaseModel \
		--use-standard-collections \
		--use-union-operator \
		--field-constraints \
		--formatters ruff-format
	@echo "models/schemas.py regenerated from openapi.yaml"

db:
	docker compose up -d
	@echo "Waiting for Postgres to be ready..."
	@until docker compose exec db pg_isready -U automation; do sleep 1; done

migrate:
	alembic -c db/alembic.ini upgrade head

seed:
	python config/seed_schemas.py

setup: install db migrate seed
	@echo "Setup complete — run 'make dev' to start the server"

dev: 
	python main.py

test:
	pytest tests/ -v
