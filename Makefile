.PHONY: install
install: ## Install the rye environment
	@echo "🚀 Creating virtual environment using rye and uv"
	rye sync

.PHONY: check
check: ## Run the quality checks on the code
	@echo "🚀 Running quality checks"
	rye run ruff .
	rye run pyright .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	rye run pytest


.PHONY: docs
docs:  ## Build and serve the documentation
	@echo "🚀 Testing documentation: Building and testing"
	mkdocs serve

.PHONY: deploy-docs
deploy-docs: ## Build and serve the documentation
	@echo "🚀 Deploying documentation"
	python deploy_docs.py


.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@rye run mkdocs build -s

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
