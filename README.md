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

Detalhes da separação e do alvo: [ADR-0004](docs/adr/0004-target-maturity-leakage.md), [ADR-0005](docs/adr/0005-reference-production-split.md) e [data card](docs/data_card.md).

## Documentação

Índice em [docs/README.md](docs/README.md).
