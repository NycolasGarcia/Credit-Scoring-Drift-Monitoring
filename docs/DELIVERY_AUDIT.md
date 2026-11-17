# Auditoria de entrega

Conferência dos critérios de avaliação e dos requisitos obrigatórios do enunciado, um a um, com o caminho da evidência no repositório. Situação em 2026-11-17.

## Critérios de avaliação

| # | Critério | Peso | Evidência | Situação |
|---|---|---|---|---|
| R1 | Validação de dados: contrato configurado, interceptando anomalias; lote ruim bloqueado com evidência | 25% | Contrato Pandera com 18 regras ([DATA_CONTRACTS.md](DATA_CONTRACTS.md), `src/contracts/`); lote com 13 defeitos bloqueado, 0 linhas pontuadas (`docs/evidence/contracts/bad-all-seed7.json`); teste de falha isolada por regra (`tests/test_contracts.py`); [ADR-0008](adr/0008-data-contracts.md) | ok |
| R2 | Detecção de drift: simulação + relatório Evidently apontando as variáveis degradadas (PSI/KS) | 25% | Simulador com ground truth ([SCENARIOS.md](SCENARIOS.md)); relatório HTML do Evidently por cenário (`docs/evidence/drift/S*_evidently.html`); PSI e KS próprios cruzados com o Evidently ([DRIFT_EVALUATION.md](DRIFT_EVALUATION.md)); robustez em 5 seeds ([ROBUSTNESS.md](ROBUSTNESS.md)); [ADR-0009](adr/0009-drift-detection-methodology.md) | ok |
| R3 | Observabilidade e logs: apresentação visual das métricas de saúde do modelo e dos alertas | 20% | Dashboard do Grafana como código (`monitoring/grafana/`) com prints em `docs/evidence/observability/`; [METRICS.md](METRICS.md), [ALERTS.md](ALERTS.md), [RUNBOOK.md](RUNBOOK.md); MLflow experimento `monitoring` | ok; prints dos painéis de resposta e de fairness pendentes (exige a stack no ar) |
| R4 | Governança (LGPD): privacidade, base legal e mitigação de vieses, consolidada no README | 15% | README, seção "Governança e Causalidade"; [GOVERNANCE.md](GOVERNANCE.md); [FAIRNESS.md](FAIRNESS.md); [ADR-0014](adr/0014-privacy-legal-basis-retention.md), [ADR-0015](adr/0015-bias-mitigation.md) | ok |
| R5 | Vídeo STAR ≤ 5 min | 15% | Roteiro cronometrado em [video_script.md](video_script.md) | **pendente: gravação pelo autor** |

## Requisitos obrigatórios

| # | Requisito | Evidência | Situação |
|---|---|---|---|
| RO-1 | Pipeline de validação de dados (data contracts) configurado | `src/contracts/`, `config/contracts/`, etapa `validate` do job | ok |
| RO-2 | Scripts de simulação e detecção estatística de drift | `src/simulation/`, `src/monitoring/`; `make simulate`, `make detect` | ok |
| RO-3 | Dashboards ou relatórios HTML comprovando o monitoramento | Relatórios Evidently em `docs/evidence/drift/`; dashboard e prints em `docs/evidence/observability/` | ok |
| RO-4 | Documentação consolidada de governança no README | README, seção "Governança e Causalidade" | ok |
| RO-5 | Histórico de commits semântico e organizado | Commits no formato Conventional Commits, verificados pelo hook `commit-msg` | ok |
| RO-6 | Scikit-Learn/XGBoost · Pandera/Great Expectations · Evidently/Alibi | scikit-learn e XGBoost (`src/models/`), Pandera (`src/contracts/`), Evidently 0.7.23 (`src/monitoring/evidently_report.py`); versões exatas no `uv.lock` | ok |
| RO-7 | Separação clara referência × produção | [ADR-0005](adr/0005-reference-production-split.md); `docs/evidence/data/split_manifest.json`; teste de interseção zero de ids | ok |
| RO-8 | ≥ 3 regras rígidas de qualidade | 11 regras bloqueantes (H01–H11) em [DATA_CONTRACTS.md](DATA_CONTRACTS.md) | ok |
| RO-9 | Relatório estatístico da mudança de distribuição (PSI ou KS) | PSI e KS por feature e lote em `docs/evidence/drift/S*.json`; [DRIFT_EVALUATION.md](DRIFT_EVALUATION.md) | ok |
| RO-10 | Compliance com plano de privacidade (PII, base legal, retenção) | [GOVERNANCE.md](GOVERNANCE.md) seções 1 a 6; [data_inventory.md](data_inventory.md); `config/governance/retention.yaml` e `make retention` | ok |
| RO-11 | Drift em ≥ 2 variáveis importantes + predições sobre o dado de produção | S1: juros, renda e DTI, 1ª, 3ª e 9ª em importância (RUN-20261113-sim-S1-03); predições em todos os lotes (RUN-20261113-sim-S0-01 a S5-01) | ok |
| RO-12 | Lote com erros forçado pelo contrato, com falha e bloqueio da ingestão | `make validate-bad`; `docs/evidence/contracts/bad-all-seed7.json` (status `blocked`, exit code 2) | ok |
| RO-13 | Logs de execução (sucesso/falha de ingestão e transformação) + resultados de drift centralizados | Eventos JSON por etapa e lote (`logs/<run_id>.jsonl`, exemplo versionado em `docs/evidence/observability/run_log_S4.jsonl`); MLflow `monitoring` | ok |
| RO-14 | Métricas de saúde operacional (status, latência, volume, alertas) | [METRICS.md](METRICS.md): status e duração por etapa, linhas por estágio, alertas por severidade, dead man's switch | ok |
| RO-15 | Análise causal ("Governança e Causalidade" no README) | [CAUSAL_ANALYSIS.md](CAUSAL_ANALYSIS.md); resumo no README | ok |
| RO-16 | Vídeo STAR (S/T/A/R com relatório, alertas e lições) | [video_script.md](video_script.md), com o checklist do critério | **pendente: gravação** |
| RO-17 | Dataset tabular financeiro binário com ≥ 5.000 amostras | Lending Club; referência de 2013 com 107.843 empréstimos maduros ([data_card.md](data_card.md)) | ok |

## Verificações técnicas

| Verificação | Resultado |
|---|---|
| Lint (ruff) | 0 erros |
| Testes | 240 passando, inclusive numa instalação limpa a partir do `uv.lock` |
| CI no último push | verde |
| Verificação de publicação (arquivos e histórico inteiro) | ok |
| Stack (`docker compose up`) do zero | **pendente: Docker parado nesta máquina** |

## Pendências para fechar a entrega

1. Subir a stack do zero (`make stack-up`), rodar um replay e refazer os prints do dashboard, agora com os painéis de resposta e de fairness (`make replay`, `make screenshots`).
2. Gravar o vídeo seguindo o roteiro e incluir o link no README.
3. Decidir a visibilidade do repositório e fazer o push final.
