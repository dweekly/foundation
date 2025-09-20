.PHONY: help build clean serve install format lint check

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install dependencies
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

build:  ## Build the website
	. venv/bin/activate && python3 build.py

clean:  ## Clean and rebuild
	. venv/bin/activate && python3 build.py --clean

serve:  ## Serve the website locally
	cd dist && python3 -m http.server 8000

format:  ## Format Python code with black
	. venv/bin/activate && black build.py

lint:  ## Lint Python code with ruff
	. venv/bin/activate && ruff check build.py

check:  ## Run all checks (format, lint)
	$(MAKE) format
	$(MAKE) lint