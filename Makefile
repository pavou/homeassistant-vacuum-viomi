INTEGRATION_FOLDER=custom_components
TEST_FOLDER=tests/

ALL_FOLDERS = $(INTEGRATION_FOLDER) $(TEST_FOLDER)

lint: ruff format-check mypy
lintfix: ruff-fix format

ruff:
	uv run ruff check $(ALL_FOLDERS)

ruff-fix:
	uv run ruff check --fix $(ALL_FOLDERS)

format:
	uv run ruff format $(ALL_FOLDERS)

format-check:
	uv run ruff format --check $(ALL_FOLDERS)

mypy:
	uv run mypy $(ALL_FOLDERS)

test:
	uv run pytest $(TEST_FOLDER)

coverage:
	uv run pytest --cov-report xml --cov=custom_components.xiaomi_viomi $(TEST_FOLDER)

coverage-html:
	uv run pytest --cov-report html --cov=custom_components.xiaomi_viomi $(TEST_FOLDER)
