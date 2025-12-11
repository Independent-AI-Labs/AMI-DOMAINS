# Domains Module Makefile

UV ?= uv
PYTHON_VERSION ?= 3.12

.PHONY: setup test clean setup-marketing

setup: setup-marketing
	@echo "Syncing domains dependencies..."
	$(UV) python install $(PYTHON_VERSION)
	$(UV) sync --dev

setup-marketing:
	@echo "Setting up marketing domain..."
	$(MAKE) -C marketing setup

test:
	$(UV) run pytest -q

clean:
	rm -rf .venv
	$(MAKE) -C marketing clean
