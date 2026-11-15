# Single command interface for the project. Recipes are shell-agnostic (sh or cmd).
RUN := uv run
SCENARIO ?= all
VINTAGE ?= 2014-01
DEFECTS ?= all

define todo
	@echo target $@ is not implemented yet - planned for $(1)
	@exit 1
endef

.PHONY: help setup lint format test data inventory eda cost train validate validate-bad contracts-d6 \
        contracts-doc simulate calibrate detect sweep-l4 drift-docs monitor \
        replay report rollback stack-up stack-down publish-check publish-check-all \
        publish-check-history

help:
	@echo dev:     setup lint format test
	@echo data:    data inventory eda
	@echo model:   train report cost
	@echo contracts: validate validate-bad contracts-d6 contracts-doc
	@echo monitor: simulate calibrate detect sweep-l4 drift-docs monitor replay rollback
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
	$(RUN) python -m src.contracts.cli --vintage $(VINTAGE) --evidence

validate-bad:
	$(RUN) python -m src.contracts.cli --bad --defects $(DEFECTS) --evidence --expect-blocked

contracts-d6:
	$(RUN) python -m src.contracts.cli --d6-sweep

contracts-doc:
	$(RUN) python -m src.contracts.catalog

simulate:
	$(RUN) python -m src.simulation.cli --scenario $(SCENARIO)

calibrate:
	$(RUN) python -m src.monitoring.cli calibrate

detect:
	$(RUN) python -m src.monitoring.cli detect --scenario $(SCENARIO)

sweep-l4:
	$(RUN) python -m src.monitoring.cli sweep-l4

drift-docs:
	$(RUN) python -m src.monitoring.docs

monitor:
	$(call todo,F6)

replay:
	$(call todo,F6)

report:
	$(RUN) python -m src.reporting.experiments

cost:
	$(RUN) python -m src.models.cost_calibration

rollback:
	$(call todo,F7)

stack-up:
	docker compose up -d

stack-down:
	docker compose down
