.PHONY: up down build logs shell-api shell-db migrate revision seed seed-rbac seed-demo test lint fmt demo demo-all demo-loop

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec db psql -U sentris_migrator -d sentris

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

seed:
	docker compose exec api python -m app.db.seeds.seed_mitre

seed-rbac:
	docker compose exec api python -m app.db.seeds.seed_rbac

seed-demo:
	docker compose exec api python -m app.db.seeds.seed_demo

test:
	docker compose exec api pytest

lint:
	docker compose exec api ruff check .
	docker compose exec api mypy app

fmt:
	docker compose exec api ruff format .

demo:
	docker compose exec api python -m simulator.replay --dataset simulator/datasets/brute_force_scenario.json

demo-all:
	docker compose exec api python -m simulator.replay --all

demo-loop:
	docker compose exec api python -m simulator.replay --all --loop --speed 3
