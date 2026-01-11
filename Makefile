# Makefile for Koru ATS

.PHONY: help install dev worker celery migrate upgrade downgrade test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run FastAPI dev server"
	@echo "  make worker       - Run Celery worker"
	@echo "  make celery       - Run Celery with beat scheduler"
	@echo "  make migrate      - Create new database migration"
	@echo "  make upgrade      - Apply database migrations"
	@echo "  make downgrade    - Rollback last migration"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache files"

install:
	poetry install

dev:
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	poetry run celery -A workers.celery_app worker --loglevel=info --concurrency=4

celery:
	poetry run celery -A workers.celery_app worker --beat --loglevel=info

migrate:
	poetry run alembic revision --autogenerate -m "$(message)"

upgrade:
	poetry run alembic upgrade head

downgrade:
	poetry run alembic downgrade -1

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check .
	poetry run mypy .

format:
	poetry run ruff format .
	poetry run ruff check --fix .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
