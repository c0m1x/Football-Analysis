SHELL := /bin/bash

COMPOSE ?= docker compose
SCRAPER ?= python3 scrapper/scrapper.py
SCRAPER_EXPORT_DIR ?= data/scraper_exports
STAMP_DIR ?= data
TEAM ?=

.PHONY: help scrape run

help:
	@echo "Targets:"
	@echo "  make scrape           Run scraper and create a session stamp"
	@echo "  make run TEAM=<name>  Run stack only if scraping was done for that team"
	@echo ""
	@echo "Examples:"
	@echo "  make scrape"
	@echo "  make run TEAM=\"Moreirense\""

scrape:
	@echo "Running scraper..."
	@$(SCRAPER)
	@python3 create_stamp.py

run:
	@python3 check_stamp.py
	@echo "Starting services..."
	@$(COMPOSE) up --build
