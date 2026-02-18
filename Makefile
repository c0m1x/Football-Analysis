SHELL := /bin/bash

COMPOSE ?= docker compose

.PHONY: help run up down logs

help:
	@echo "Targets:"
	@echo "  make up      Build and start stack"
	@echo "  make down    Stop stack"
	@echo "  make logs    Follow backend logs"
	@echo "  make run     Alias for up"

up:
	@$(COMPOSE) up --build

run: up

down:
	@$(COMPOSE) down

logs:
	@$(COMPOSE) logs -f backend
