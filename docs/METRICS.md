# Catálogo de métricas

> Gerado por `make alerts` (`src/observability/metrics.py`). Não editar.

Todas as métricas são gauges publicados pelo job no Pushgateway, no grupo `job=cdm_monitoring, scenario=<id>`; cada push substitui o estado do lote anterior ([ADR-0010](adr/0010-observability-stack.md)).

| Métrica | Tipo | Rótulos | Grupo | Significado | Painel |
|---|---|---|---|---|---|
| `cdm_batch_index` | gauge | — | operacional | Índice do lote no cenário (eixo do replay) | Lote e mês |
| `cdm_batch_info` | gauge | `batch_id`, `issue_month` | operacional | Lote processado (valor 1; mês simulado no rótulo) | Lote e mês |
| `cdm_step_status` | gauge | `step` | operacional | Etapa do job: 1 concluída, 0 falhou, -1 pulada | Saúde do pipeline |
| `cdm_step_duration_seconds` | gauge | `step` | operacional | Duração da etapa | Duração por etapa |
| `cdm_batch_duration_seconds` | gauge | — | operacional | Duração total do lote | Duração por etapa |
| `cdm_batch_rows` | gauge | `stage` | operacional | Linhas por estágio: in, valid, quarantined, scored | Volume e quarentena |
| `cdm_gate_blocked` | gauge | — | operacional | 1 se o contrato bloqueou o lote | Volume e quarentena |
| `cdm_last_success_timestamp_seconds` | gauge | — | operacional | Fim do último lote concluído (dead man's switch) | Saúde do pipeline |
| `cdm_feature_psi` | gauge | `feature` | dados | PSI da feature contra os bins da referência | PSI por feature e lote |
| `cdm_features_drifted` | gauge | — | dados | Features com PSI acima do SEV-1 | PSI por feature e lote |
| `cdm_score_psi` | gauge | — | modelo | PSI do score contra os decis da referência | Score e aprovação |
| `cdm_approval_rate` | gauge | — | modelo | Taxa de aprovação do lote | Score e aprovação |
| `cdm_expected_bad_rate` | gauge | — | modelo | Bad rate esperado (média do score) | Score e aprovação |
| `cdm_observed_bad_rate` | gauge | — | modelo | Bad rate observado nos rótulos que amadurecem | Desempenho com rótulo maduro |
| `cdm_bad_rate_ratio` | gauge | — | modelo | Observado / esperado nos rótulos que amadurecem | Desempenho com rótulo maduro |
| `cdm_auc_mature` | gauge | — | modelo | AUC dos rótulos que amadurecem | Desempenho com rótulo maduro |
| `cdm_labeled_rows` | gauge | — | modelo | Rótulos que amadurecem no lote | Desempenho com rótulo maduro |
| `cdm_signal_severity` | gauge | `signal` | alertas | Severidade por sinal (0-3) | Severidade por sinal |
| `cdm_batch_severity` | gauge | — | alertas | Severidade do lote (máximo dos sinais) | Severidade por sinal |
| `cdm_alert_level` | gauge | `alert` | alertas | Nível do alerta (0-3), lido pelas regras do Prometheus | Alertas |
| `cdm_alerts_firing` | gauge | `severity` | alertas | Alertas ativos no lote por severidade | Alertas |
| `cdm_diagnosis` | gauge | `code` | alertas | Diagnóstico do lote (valor 1 no código vigente) | Diagnóstico |
| `cdm_conservative_mode` | gauge | — | resposta | 1 se o modo conservador (GR-4) está ativo | Resposta |
| `cdm_policy_threshold` | gauge | — | resposta | Limiar de política do modo conservador no lote | Resposta |
| `cdm_kill_switch` | gauge | — | resposta | 1 se a decisão automática está suspensa (GR-9) | Resposta |
| `cdm_policy_rule` | gauge | `rule` | resposta | Regra da matriz de resposta aplicada (valor 1) | Resposta |
| `cdm_decisions` | gauge | `decision` | resposta | Decisões finais do lote: approve, review, reject | Resposta |
