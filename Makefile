# Single command interface for the project. Recipes are shell-agnostic (sh or cmd).
RUN := uv run
SCENARIO ?= S1

define todo
	@echo target $@ is not implemented yet - planned for $(1)
	@exit 1
endef

.PHONY: help setup lint format test data inventory eda train validate validate-bad simulate detect monitor \
        replay report rollback stack-up stack-down publish-check publish-check-all \
        publish-check-history

help:
	@echo dev:     setup lint format test
	@echo data:    data inventory eda
	@echo model:   train report
	@echo monitor: validate validate-bad simulate detect monitor replay rollback
	@echo stack:   stack-up stack-down
	@echo publish: publish-check publish-check-all publish-check-history

setup:
	uv sync --frozen
	$(RUN) pre-commit install

lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format:
	$(RUN) ruff format .
	$(RUN) ruff check --fix .

test:
	$(RUN) pytest

publish-check:
	$(RUN) python scripts/check_publication.py --staged

publish-check-all:
	$(RUN) python scripts/check_publication.py --all

publish-check-history:
	$(RUN) python scripts/check_publication.py --history

data:
	$(RUN) python -m src.data.prepare

inventory:
	$(RUN) python -m src.data.inventory

eda:
	$(RUN) jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb

train:
	$(RUN) python -m src.models.train

validate:
	$(call todo,F3)

validate-bad:
	$(call todo,F3)

simulate:
	$(call todo,F4)

detect:
	$(call todo,F5)

monitor:
	$(call todo,F6)

replay:
	$(call todo,F6)

report:
	$(RUN) python -m src.reporting.experiments

rollback:
	$(call todo,F7)

stack-up:
	docker compose up -d

stack-down:
	docker compose down
