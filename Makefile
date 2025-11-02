# Makefile for E-commerce Microservices Project
include .env
export $(shell sed 's/=.*//' .env)
.PHONY: help test build up down lint format

help:
	@echo "Available commands:"
	@echo "  make test         Run all pytest tests"
	@echo "  make test-unit    Run only unit tests"
	@echo "  make test-int     Run integration tests (requires Kafka)"
	@echo "  make test-e2e     Run end-to-end tests with docker-compose.test.yml"
	@echo "  make build        Build all Docker images"
	@echo "  make up           Start services via docker-compose"
	@echo "  make down         Stop all services"

test:
	pytest -v --maxfail=1 --disable-warnings

test-unit:
	pytest -v -s user_service/tests
	pytest -v order_service/tests

test-int:
	docker compose -f docker-compose.test.yml up -d kafka db
	pytest -v -m "integration" || true
	docker compose -f docker-compose.test.yml down
