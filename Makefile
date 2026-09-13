.PHONY: install
install: ## Install the uv environment
	@echo "🚀 Creating virtual environment using uv"
	uv sync --locked

.PHONY: check
check: ## Run the quality checks on the code
	@echo "🚀 Running quality checks"
	uv run --locked ruff check .
	uv run --locked pyright .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	uv run --locked pytest


.PHONY: docs
docs:  ## Build and serve the documentation
	@echo "🚀 Testing documentation: Building and testing"
	uv run --locked mkdocs serve

.PHONY: deploy-docs
deploy-docs: ## Build and serve the documentation
	@echo "🚀 Deploying documentation"
	uv run --locked python deploy_docs.py


.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@uv run --locked mkdocs build -s

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
