.PHONY: isort
isort:
	ruff check --select I --fix

.PHONY: check
check:
	ruff check

.PHONY: check-fix
check-fix:
	ruff check --fix 

.PHONY: check-imports
check-imports:
	ruff check --select F401 --fix

.PHONY: test
test:
	pytest app/tests/ -v --tb=short

.PHONY: test-verbose
test-verbose:
	pytest app/tests/ -vv --tb=long

.PHONY: test-docker
test-docker:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test

.PHONY: test-coverage
test-coverage:
	pytest app/tests/ --cov=app --cov-report=html --cov-report=term

.PHONY: test-specific
test-specific:
	@echo "Usage: make test-specific TEST=test_file.py::TestClass::test_method"
	@echo "Example: make test-specific TEST=app/tests/test_api.py::TestEventEndpoints::test_create_event"

.PHONY: clean-test
clean-test:
	rm -f test_ticket.db
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

.PHONY: help
help:
	@echo "Available test commands:"
	@echo "  make test           - Run all tests locally"
	@echo "  make test-verbose   - Run tests with verbose output"
	@echo "  make test-docker    - Run tests in Docker environment"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make clean-test     - Clean test artifacts"