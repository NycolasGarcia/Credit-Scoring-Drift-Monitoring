# Credit Scoring — Monitoramento de Drift e Resposta à Degradação

Sustentação e confiabilidade de um modelo de credit scoring em produção simulada: contratos de dados, detecção de drift, observabilidade, guardrails e governança (LGPD).

> Projeto em construção. O progresso por fase está em [docs/PROGRESS.md](docs/PROGRESS.md).

## Setup

Requisitos: [uv](https://docs.astral.sh/uv/), Git e GNU Make (Docker a partir da etapa de observabilidade).

```bash
make setup     # uv sync --frozen + instala os hooks de pre-commit
make lint
make test
make help      # lista todos os comandos
```

### Dados

1. Baixe o dataset "All Lending Club loan data" no Kaggle (`wordsforthewise/lending-club`, licença CC0) e extraia `accepted_2007_to_2018Q4.csv` dentro de `data/raw/` (fora do git).
2. Copie `.env.example` para `.env` e preencha:
   - `CDM_RAW_DATA_PATH`: caminho do CSV, relativo à raiz do projeto;
   - `CDM_PSEUDONYMIZATION_KEY`: chave aleatória, gerada com `python -c "import secrets; print(secrets.token_hex(32))"`. Guarde-a: os hashes das partições dependem dela.
3. Gere as partições e a EDA:

```bash
make data      # referência / holdout / produção em data/processed + manifesto em docs/evidence/data
make eda       # executa notebooks/01_eda.ipynb (somente agregados)
make inventory # regenera docs/data_inventory.md e a lista de PII a partir do inventário
```

### Modelo

```bash
make train     # dummy, regressão logística e XGBoost; calibra, seleciona e registra o champion no MLflow
make report    # regenera docs/EXPERIMENTS.md a partir do MLflow
make cost      # estima LGD e margem do caixa realizado e valida o limiar (FP/FN) contra o caixa real
```

Cada treino gera RUN records em `docs/runs/` e o perfil de referência em `models/reference_profile.json`. Resultados: [EXPERIMENTS.md](docs/EXPERIMENTS.md).

### Contratos de dados (quality gate)

```bash
make validate VINTAGE=2014-01   # valida, põe em quarentena linhas inválidas e pontua um mês real
make validate-bad               # injeta 13 defeitos catalogados; sucesso = lote BLOQUEADO (0 linhas pontuadas)
make validate-bad DEFECTS=monthly_income   # um defeito isolado (renda mensal no lugar de anual)
make contracts-d6               # varredura do bug de unidade: o que o contrato pega e o que fica para o drift
make contracts-doc              # regenera docs/DATA_CONTRACTS.md a partir das regras e da configuração
```

Lote bloqueado → exit code 2, linhas e relatório agregado em `data/quarantine/<batch_id>/`, evidência em `docs/evidence/contracts/`. Regras: [DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md); decisões: [ADR-0008](docs/adr/0008-data-contracts.md).

### Cenários de degradação

```bash
make simulate                  # S0..S5: lotes mensais com drift controlado, passados pelo gate e pontuados
make simulate SCENARIO=S2      # um cenário
```

S0 controle · S1 choque econômico (D1) · S2 concept drift (D3) · S3 prior shift (D2) · S4 bug de unidade (D6) · S5 produção natural. Lotes em `data/simulated/` (fora do git), manifestos de ground truth em `docs/evidence/scenarios/` e um RUN record por cenário. Detalhes: [SCENARIOS.md](docs/SCENARIOS.md) e [ADR-0017](docs/adr/0017-scenario-simulator.md).

### Detecção de drift

```bash
make calibrate                 # bootstrap A/A no controle: falso alarme por sinal e limiares calibrados
make detect                    # detector em todos os cenários: severidade, diagnóstico, Evidently e avaliação
make detect SCENARIO=S2
make drift-docs                # regenera docs/THRESHOLDS.md e docs/DRIFT_EVALUATION.md
```

Camadas L2 (drift por feature), L3 (score e aprovação) e L4 (desempenho com rótulo maduro), diagnóstico D0/D1/D2/D3/D4/D6 e um relatório HTML do Evidently por cenário em `docs/evidence/drift/`. Detalhes: [ADR-0009](docs/adr/0009-drift-detection-methodology.md), [THRESHOLDS.md](docs/THRESHOLDS.md) e [DRIFT_EVALUATION.md](docs/DRIFT_EVALUATION.md).

Detalhes da separação e do alvo: [ADR-0004](docs/adr/0004-target-maturity-leakage.md), [ADR-0005](docs/adr/0005-reference-production-split.md) e [data card](docs/data_card.md).

## Documentação

Índice em [docs/README.md](docs/README.md). Mudanças por fase: [CHANGELOG.md](CHANGELOG.md).
