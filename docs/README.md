# Documentação do projeto

Ponto de entrada da documentação. Status de cada documento entre parênteses.

| Documento | Para quê | Status |
|---|---|---|
| [PROGRESS.md](PROGRESS.md) | Log append-only de checkpoints por fase | vivo |
| [../CHANGELOG.md](../CHANGELOG.md) | Mudanças por fase, em ordem cronológica | vivo |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes e fluxos (treino, monitoramento, resposta) | dados (F1), treino (F2), quality gate (F3), simulador (F4), detecção (F5), observabilidade (F6) e resposta (F7) implementados |
| [adr/](adr/) | Decisões de arquitetura | ver índice abaixo |
| [runs/INDEX.md](runs/INDEX.md) | Registro de execuções (todo número citado aponta para um RUN-id) | gerado (treino, calibração, simulação, monitoramento e resposta) |
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
| [METRICS.md](METRICS.md) | Catálogo de métricas do job (gerado) | gerado |
| [ALERTS.md](ALERTS.md) | Catálogo de alertas com severidade, ação e playbook (gerado) | gerado |
| [RUNBOOK.md](RUNBOOK.md) | Stack, job, replay, prints, solução de problemas e playbook por alerta | F6 |
| [evidence/observability/](evidence/observability/) | Prints do painel do Grafana após os replays | F6 |
| [RESPONSE_EVALUATION.md](RESPONSE_EVALUATION.md) | Comparação de respostas por cenário, com valor em US$ (gerado) | gerado |
| [response_notes.md](response_notes.md) | Leitura humana da comparação de respostas (incluída no RESPONSE_EVALUATION) | F7 |
| [evidence/response/](evidence/response/) | Comparação de respostas, avaliação em sombra e ensaio de promoção/rollback | F7 |

Documentos previstos para fases seguintes: `CAUSAL_ANALYSIS.md`, `GOVERNANCE.md`, `video_script.md`.

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
| [0010](adr/0010-observability-stack.md) | Stack de observabilidade: Pushgateway, Prometheus, Grafana como código, replay em tempo real | aceito |
| [0011](adr/0011-severity-alert-policy.md) | Severidade e política de alertas: uma fonte para os cortes, dead man's switch | aceito |
| [0012](adr/0012-guardrails-conservative-mode.md) | Guardrails e modo conservador: matriz declarativa, breaker com histerese, faixa cinza para revisão | aceito |
| [0013](adr/0013-retraining-gate-rollback.md) | Recalibração e retreino em janela recente, travas GR-7/GR-8, gate GR-5, rollback por aliases | aceito |
| [0016](adr/0016-empirical-cost-threshold.md) | Premissas de custo empíricas, funding e apetite de risco | aceito |
| [0017](adr/0017-scenario-simulator.md) | Desenho do simulador de cenários: amostragem, rótulo por oráculo, atraso de rótulo, S4 parcial | aceito |
| [0018](adr/0018-l4-sev2-cut.md) | Corte de SEV-2 da razão observado/esperado: 1,25 por regra nula declarada antes, validado em variantes novas | aceito |
| [0019](adr/0019-conservative-mode-by-value.md) | Modo conservador por valor esperado com risco corrigido (supersede o item 3 do 0012) | aceito |
| [0020](adr/0020-relative-calibration-gate.md) | Calibração do gate relativa ao champion (supersede o critério absoluto do 0013) | aceito |
