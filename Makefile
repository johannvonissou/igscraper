.DEFAULT_GOAL := help

.PHONY: help build check clean

help:
	@echo "make build   : installe les dépendances et Chrome"
	@echo "make check   : lint + vérification de la syntaxe"
	@echo "make clean   : supprime .venv, vendor, le profil et le lock"
	@echo "make help    : affiche l'aide"

build:
	uv sync
	uv run igscraper chrome install	

check:
	uvx ruff check igscraper
	uv run python -m compileall -q igscraper

clean:
	rm -rf .venv vendor .chrome-profile uv.lock dist .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
