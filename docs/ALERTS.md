# Catálogo de alertas

> Gerado por `make alerts` (`src/alerting/rules.py`) a partir de `config/monitoring/alerts.yaml`. Não editar à mão.

Os cortes dos sinais estão em [THRESHOLDS.md](THRESHOLDS.md); as regras do Prometheus, em `monitoring/rules/cdm_alerts.yml`. Decisões: [ADR-0011](adr/0011-severity-alert-policy.md).
Dono de todos os alertas: time de risco de modelos. Dead man's switch: dispara após 30 s sem lote concluído com sucesso.

| Id | Alerta | Camada | Severidade | Diagnóstico | Ação (§8.5) | Playbook |
|---|---|---|---|---|---|---|
| `CDM_CONTRACT_BLOCKED` | Lote bloqueado pelo contrato de dados | L0 | SEV-2 · SEV-3 com 2 lotes bloqueados seguidos | D0 | A2 quarentena + A1 alertar; corrigir na fonte e reprocessar (GR-1, GR-2) | [playbook](RUNBOOK.md#cdm_contract_blocked) |
| `CDM_SOFT_RULES` | Regra de aviso do contrato disparou | L0 | SEV-1 | D0 | A0 registrar; revisar a regra e a fonte no ciclo seguinte | [playbook](RUNBOOK.md#cdm_soft_rules) |
| `CDM_UNIT_BUG_SUSPECTED` | Assinatura de bug de unidade (fator constante numa feature) | L2 | SEV-2 | D6 | A2 quarentena preventiva; confirmar com a fonte; nunca retreinar (GR-7) | [playbook](RUNBOOK.md#cdm_unit_bug_suspected) |
| `CDM_FEATURE_DRIFT` | Drift de entrada por feature | L2 | SEV-1 a 3 conforme [`feature_psi`](THRESHOLDS.md) | D1 | SEV-1 registrar e revisar; SEV-2+ com score estável segue D1 benigno, com score em drift vai a modo conservador (§8.7) | [playbook](RUNBOOK.md#cdm_feature_drift) |
| `CDM_SCORE_DRIFT` | Drift da distribuição do score | L3 | SEV-1 a 3 conforme [`score_psi`](THRESHOLDS.md) | D4 | SEV-2 com rótulo imaturo → A4 modo conservador + A3 análise causal (GR-4) | [playbook](RUNBOOK.md#cdm_score_drift) |
| `CDM_APPROVAL_SHIFT` | Taxa de aprovação fora da banda | L3 | SEV-1 a 3 conforme [`approval_delta_pp`](THRESHOLDS.md) | D4 | SEV-2 → A4 modo conservador (GR-3, GR-4); conferir antes se é bug de dado (D6) | [playbook](RUNBOOK.md#cdm_approval_shift) |
| `CDM_BAD_RATE_RATIO` | Bad rate observado descolado do esperado (rótulo maduro) | L4 | SEV-1 a 3 conforme [`bad_rate_ratio`](THRESHOLDS.md) | D2 | AUC estável → A5 recalibrar; descolamento concentrado num segmento → D3, A6 challenger em sombra | [playbook](RUNBOOK.md#cdm_bad_rate_ratio) |
| `CDM_AUC_DROP` | Queda de AUC na coorte madura | L4 | SEV-1 a 3 conforme [`auc_drop`](THRESHOLDS.md) | D3 | A4 modo conservador + A6 challenger em sombra → gate de promoção (GR-5) | [playbook](RUNBOOK.md#cdm_auc_drop) |
| `CDM_FAIRNESS_GAP` | A decisão abriu gap de aprovação entre grupos (fairness drift) | L3 | SEV-1 se o gap cresce > 3 p.p.; SEV-2 se > 7 p.p. (`config/governance/fairness.yaml`) | D4 | A1 alertar; conferir o segmento e o limite do modo conservador (ADR-0015); SEV-2 → A3 revisão de fairness | [playbook](RUNBOOK.md#cdm_fairness_gap) |
| `CDM_STEP_FAILED` | Etapa do pipeline falhou | L1 | SEV-2 | D5 | A1 alertar; ver o evento da etapa no log do run e reprocessar o lote | [playbook](RUNBOOK.md#cdm_step_failed) |
| `CDM_PIPELINE_SLOW` | Duração do lote acima de 2x a mediana do run | L1 | SEV-1 | D5 | A0 registrar; investigar volume e etapa mais lenta | [playbook](RUNBOOK.md#cdm_pipeline_slow) |
| `CDM_MONITOR_STALE` | Monitor parado (dead man's switch) | L1 | SEV-3 | D5 | A1 alertar; restaurar o job — sem monitor, "nenhum alerta" não significa "tudo bem" (GR-11) | [playbook](RUNBOOK.md#cdm_monitor_stale) |
