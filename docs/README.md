# Documentação do projeto

Ponto de entrada da documentação. Status de cada documento entre parênteses.

| Documento | Para quê | Status |
|---|---|---|
| [PROGRESS.md](PROGRESS.md) | Log append-only de checkpoints por fase | vivo |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes e fluxos (treino, monitoramento, resposta) | dados implementados (F1); demais planejados |
| [adr/](adr/) | Decisões de arquitetura | ver índice abaixo |
| [runs/INDEX.md](runs/INDEX.md) | Registro de execuções (todo número citado aponta para um RUN-id) | vazio |
| [incidents/](incidents/) | Incidentes e postmortems | vazio |
| [evidence/](evidence/) | Prints e relatórios curados (somente agregados) | vivo |
| [data_inventory.md](data_inventory.md) | Classificação das 151 colunas (gerado do YAML) | gerado |
| [data_card.md](data_card.md) | Origem, licença, volume por safra, alvo, limitações | F1 |
| [../notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb) | EDA: volume, censura, maturação, nulos, PSI anual | F1 |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Comparação dos runs de treino (gerado do MLflow) | gerado |
| [model_card.md](model_card.md) | Uso, desempenho, calibração, limiar, sensibilidade a drift, limitações | rascunho F2 |
| [../notebooks/02_modelagem.ipynb](../notebooks/02_modelagem.ipynb) | Curva de calibração, score fora do tempo, trade-off do limiar, importância | F2 |

Documentos previstos para fases seguintes: `DATA_CONTRACTS.md`, `SCENARIOS.md`, `DRIFT_EVALUATION.md`, `THRESHOLDS.md`, `METRICS.md`, `ALERTS.md`, `RUNBOOK.md`, `RESPONSE_EVALUATION.md`, `CAUSAL_ANALYSIS.md`, `GOVERNANCE.md`, `video_script.md`.

## ADRs

| # | Título | Status |
|---|---|---|
| [0001](adr/0001-toolchain.md) | Toolchain: uv, ruff, pytest, MLflow e versões exatas | aceito |
| [0002](adr/0002-publication-policy.md) | Política de publicação e higiene do repositório | aceito |
| [0003](adr/0003-dataset.md) | Escolha do dataset: Lending Club | aceito |
| [0004](adr/0004-target-maturity-leakage.md) | Alvo, maturação do rótulo e exclusão de vazamento | aceito |
| [0005](adr/0005-reference-production-split.md) | Separação referência × produção | aceito |
| [0006](adr/0006-base-model.md) | Modelo base: regressão logística calibrada | aceito |
| [0007](adr/0007-cost-threshold.md) | Matriz de custo e limiar por valor esperado | aceito (custos PROPOSTO) |
