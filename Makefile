# Single command interface for the project. Recipes are shell-agnostic (sh or cmd).
RUN := uv run
SCENARIO ?= all
VINTAGE ?= 2014-01
DEFECTS ?= all
INTERVAL ?= 15
REGISTRY ?= credit-scoring
JOB_SCENARIO := $(if $(filter all,$(SCENARIO)),S1,$(SCENARIO))
PROMTOOL := docker run --rm -v "$(CURDIR)/monitoring://m:ro" --entrypoint promtool prom/prometheus:v3.5.0

define todo
	@echo target $@ is not implemented yet - planned for $(1)
	@exit 1
endef

.PHONY: help setup lint format test data inventory eda cost train validate validate-bad contracts-d6 \
        contracts-doc simulate calibrate detect sweep-l4 drift-docs alerts check-rules screenshots monitor \
        replay report rollback respond-compare stack-up stack-down stack-status publish-check publish-check-all \
        publish-check-history

help:
	@echo dev:     setup lint format test
	@echo data:    data inventory eda
	@echo model:   train report cost
	@echo contracts: validate validate-bad contracts-d6 contracts-doc
	@echo monitor: simulate calibrate detect sweep-l4 drift-docs monitor replay rollback
	@echo alerts:  alerts check-rules screenshots
	@echo respond: respond-compare rollback
	@echo stack:   stack-up stack-down stack-status
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

alerts:
	$(RUN) python -m src.alerting.rules
	$(RUN) python -m src.observability.metrics
	$(RUN) python -m src.observability.dashboard

check-rules:
	$(PROMTOOL) check rules //m/rules/cdm_alerts.yml
	$(PROMTOOL) test rules //m/rules-tests/cdm_alerts_test.yml

monitor:
	$(RUN) python -m src.observability.runner --scenario $(JOB_SCENARIO)

replay:
	$(RUN) python -m src.observability.runner --scenario $(JOB_SCENARIO) --interval $(INTERVAL) --push

screenshots:
	$(RUN) python -m src.observability.screenshots --scenario $(JOB_SCENARIO)

report:
	$(RUN) python -m src.reporting.experiments

cost:
	$(RUN) python -m src.models.cost_calibration

rollback:
	$(RUN) python -m src.response.cli rollback --registry $(REGISTRY)

respond-compare:
	$(RUN) python -m src.response.cli compare

stack-up:
	docker compose up -d

stack-down:
	docker compose down

stack-status:
	docker compose ps
