# Makefile for Orchestrator project

# Docker configuration
IMAGE_NAME := mozmeao/orchestrator
PORT := 8000
DC := docker-compose

.PHONY: help install compile-requirements clean build build-builder up down restart logs shell shell-web test test-image kill env-setup

help:
	@echo "Orchestrator - Docker Management"
	@echo ""
	@echo "Setup:"
	@echo "  env-setup            Create .env from env-dist"
	@echo "  install              Install Python dependencies locally"
	@echo "  compile-requirements Compile requirements.txt from requirements.in"
	@echo ""
	@echo "Docker - Build:"
	@echo "  build                Build main image"
	@echo "  build-builder        Build builder image"
	@echo ""
	@echo "Docker - Run:"
	@echo "  up                   Start services (web, db, redis)"
	@echo "  down                 Stop and remove containers"
	@echo "  restart              Restart services"
	@echo "  logs                 View logs (follow mode)"
	@echo ""
	@echo "Docker - Testing:"
	@echo "  test                 Run tests in container with volumes"
	@echo "  test-image           Run tests in clean container (no volumes)"
	@echo ""
	@echo "Docker - Shell Access:"
	@echo "  shell                Open bash in web container"
	@echo "  shell-web            Alias for shell"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean                Remove Python artifacts"
	@echo "  kill                 Remove everything (containers, images, volumes)"

install:
	pip install -r requirements/requirements.txt

compile-requirements:
	$(DC) run --rm compile-requirements

# Docker build targets
build:
	$(DC) build web

build-builder:
	$(DC) build builder

# Docker run targets
up:
	$(DC) up -d web
	@echo "Services started. Access at http://localhost:$(PORT)"

down:
	$(DC) down

restart:
	$(DC) restart web

logs:
	$(DC) logs -f web

# Shell access
shell:
	$(DC) exec web /bin/bash

shell-web: shell

# Testing
test:
	$(DC) run --rm test

test-image:
	$(DC) run --rm test-image

# Cleanup
kill: down
	$(DC) down --rmi all --volumes --remove-orphans
	@echo "All containers, images, and volumes removed"

# Environment setup
env-setup:
	@if [ ! -f .env ]; then \
		cp env-dist .env; \
		echo "Created .env file from env-dist"; \
		echo "Please update .env with your settings"; \
		echo ""; \
		echo "Quick start:"; \
		echo "  1. Review .env file"; \
		echo "  2. Run: make build"; \
		echo "  3. Run: make up"; \
	else \
		echo ".env file already exists"; \
	fi

# Maintenance
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
