# Credit Scoring — Monitoramento de Drift e Resposta à Degradação

Sustentação e confiabilidade de um modelo de credit scoring em produção simulada: contratos de dados, detecção de drift, observabilidade, guardrails e governança (LGPD).

> Projeto em construção. O progresso por fase está em [docs/PROGRESS.md](docs/PROGRESS.md).

## Setup

Requisitos: [uv](https://docs.astral.sh/uv/), Git e GNU Make.

```bash
make setup     # uv sync --frozen + instala os hooks de pre-commit
make lint
make test
```

Copie `.env.example` para `.env` e preencha os valores locais.

## Documentação

Índice em [docs/README.md](docs/README.md).
