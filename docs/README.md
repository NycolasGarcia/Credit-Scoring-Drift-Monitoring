# Documentação do projeto

Ponto de entrada da documentação. Status de cada documento entre parênteses.

| Documento | Para quê | Status |
|---|---|---|
| [PROGRESS.md](PROGRESS.md) | Log append-only de checkpoints por fase | vivo |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes e fluxos (treino, monitoramento, resposta) | esqueleto |
| [adr/](adr/) | Decisões de arquitetura | ver índice abaixo |
| [runs/INDEX.md](runs/INDEX.md) | Registro de execuções (todo número citado aponta para um RUN-id) | vazio |
| [incidents/](incidents/) | Incidentes e postmortems | vazio |
| [evidence/](evidence/) | Prints e relatórios curados (somente agregados) | vazio |

Documentos previstos para fases seguintes: `data_inventory.md`, `data_card.md`, `EXPERIMENTS.md`, `DATA_CONTRACTS.md`, `SCENARIOS.md`, `DRIFT_EVALUATION.md`, `THRESHOLDS.md`, `METRICS.md`, `ALERTS.md`, `RUNBOOK.md`, `RESPONSE_EVALUATION.md`, `CAUSAL_ANALYSIS.md`, `GOVERNANCE.md`, `model_card.md`, `video_script.md`.

## ADRs

| # | Título | Status |
|---|---|---|
| [0001](adr/0001-toolchain.md) | Toolchain: uv, ruff, pytest, MLflow e versões exatas | aceito |
| [0002](adr/0002-publication-policy.md) | Política de publicação e higiene do repositório | aceito |
