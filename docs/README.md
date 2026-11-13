# Documentação do projeto

Ponto de entrada da documentação. Status de cada documento entre parênteses.

| Documento | Para quê | Status |
|---|---|---|
| [PROGRESS.md](PROGRESS.md) | Log append-only de checkpoints por fase | vivo |
| [../CHANGELOG.md](../CHANGELOG.md) | Mudanças por fase, em ordem cronológica | vivo |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes e fluxos (treino, monitoramento, resposta) | dados (F1), treino (F2), quality gate (F3), simulador (F4) e detecção (F5) implementados; demais planejados |
| [adr/](adr/) | Decisões de arquitetura | ver índice abaixo |
| [runs/INDEX.md](runs/INDEX.md) | Registro de execuções (todo número citado aponta para um RUN-id) | gerado (treino, calibração, simulação e monitoramento) |
| [incidents/](incidents/) | Incidentes e postmortems | vazio |
| [evidence/](evidence/) | Prints e relatórios curados (somente agregados) | vivo |
| [data_inventory.md](data_inventory.md) | Classificação das 151 colunas (gerado do YAML) | gerado |
| [data_card.md](data_card.md) | Origem, licença, volume por safra, alvo, limitações | F1 |
| [../notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb) | EDA: volume, censura, maturação, nulos, PSI anual | F1 |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Comparação dos runs de treino (gerado do MLflow) | gerado |
| [model_card.md](model_card.md) | Uso, desempenho, calibração, limiar, sensibilidade a drift, limitações | rascunho F2 |
| [../notebooks/02_modelagem.ipynb](../notebooks/02_modelagem.ipynb) | Curva de calibração, score fora do tempo, trade-off do limiar, importância | F2 |
| [DATA_CONTRACTS.md](DATA_CONTRACTS.md) | Catálogo de regras do contrato (gerado), parâmetros e caso D6 | gerado |
| [contracts_d6.md](contracts_d6.md) | Apêndice do catálogo: contrato × drift no bug de unidade (incluído no DATA_CONTRACTS) | F3 |
| [evidence/contracts/](evidence/contracts/) | Relatórios agregados do gate (mês real, lote ruim, varredura D6) | F3 |
| [SCENARIOS.md](SCENARIOS.md) | Cenários S0–S5: o que muda, quando, narrativa econômica e resultados | F4 |
| [evidence/scenarios/](evidence/scenarios/) | Manifestos de ground truth por cenário (agregados, hashes, RUN-id) | F4 |
| [THRESHOLDS.md](THRESHOLDS.md) | Limiares vigentes e calibração no controle (gerado) | gerado |
| [DRIFT_EVALUATION.md](DRIFT_EVALUATION.md) | Avaliação do detector por cenário, relatórios Evidently, p-valor × efeito (gerado) | gerado |
| [evidence/drift/](evidence/drift/) | Resultados por lote, relatórios HTML do Evidently e calibração | F5 |

Documentos previstos para fases seguintes: `METRICS.md`, `ALERTS.md`, `RUNBOOK.md`, `RESPONSE_EVALUATION.md`, `CAUSAL_ANALYSIS.md`, `GOVERNANCE.md`, `video_script.md`.

## ADRs

| # | Título | Status |
|---|---|---|
| [0001](adr/0001-toolchain.md) | Toolchain: uv, ruff, pytest, MLflow e versões exatas | aceito |
| [0002](adr/0002-publication-policy.md) | Política de publicação e higiene do repositório | aceito |
| [0003](adr/0003-dataset.md) | Escolha do dataset: Lending Club | aceito |
| [0004](adr/0004-target-maturity-leakage.md) | Alvo, maturação do rótulo e exclusão de vazamento | aceito |
| [0005](adr/0005-reference-production-split.md) | Separação referência × produção | aceito |
| [0006](adr/0006-base-model.md) | Modelo base: regressão logística calibrada | aceito |
| [0007](adr/0007-cost-threshold.md) | Matriz de custo e limiar por valor esperado | supersedido pelo 0016 |
| [0008](adr/0008-data-contracts.md) | Contratos de dados, gate em dois níveis e quarentena | aceito |
| [0009](adr/0009-drift-detection-methodology.md) | Metodologia de detecção de drift: PSI com bins fixos, efeito × p-valor, calibração, API do Evidently | aceito |
| [0016](adr/0016-empirical-cost-threshold.md) | Premissas de custo empíricas, funding e apetite de risco | aceito |
| [0017](adr/0017-scenario-simulator.md) | Desenho do simulador de cenários: amostragem, rótulo por oráculo, atraso de rótulo, S4 parcial | aceito |
