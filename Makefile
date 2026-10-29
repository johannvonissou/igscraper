CHROME_DEB_URL := https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
CHROME_BIN     := vendor/chrome/chrome

.DEFAULT_GOAL := help

.PHONY: help build check clean

help:
	@echo "make build   : installe les dépendances et Chrome"
	@echo "make check   : lint + vérification de la syntaxe"
	@echo "make clean   : supprime .venv, vendor, le profil et le lock"
	@echo "make help    : affiche l'aide"

build:
	uv sync
	@[ -f $(CHROME_BIN) ] || { \
		mkdir -p vendor; \
		curl -fSL -o /tmp/chrome.deb $(CHROME_DEB_URL); \
		( cd vendor && ar x /tmp/chrome.deb && tar -xf data.tar.xz \
			&& rm -f control.tar.xz data.tar.xz debian-binary ); \
		mv vendor/opt/google/chrome vendor/chrome; \
		rm -rf vendor/opt vendor/usr; \
	}

check:
	uvx ruff check igscraper
	uv run python -m compileall -q igscraper

clean:
	rm -rf .venv vendor .chrome-profile uv.lock dist .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +