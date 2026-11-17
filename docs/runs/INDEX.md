# Índice de execuções

Uma linha por RUN, em ordem cronológica. Gerado por `src/reporting/`.

Observações humanas sobre os runs ficam na seção "Observações" de cada registro. Runs de depuração com árvore suja não são versionados.

| RUN-id | Data | Tipo | Cenário | Veredito | Reprodutível |
|---|---|---|---|---|---|
| [RUN-20261112-train-REF-01](RUN-20261112-train-REF-01.md) | 2026-11-12 | train | REF | candidato | sim |
| [RUN-20261112-train-REF-02](RUN-20261112-train-REF-02.md) | 2026-11-12 | train | REF | champion (v1) | sim |
| [RUN-20261112-train-REF-03](RUN-20261112-train-REF-03.md) | 2026-11-12 | train | REF | candidato | sim |
| [RUN-20261113-calib-COST-01](RUN-20261113-calib-COST-01.md) | 2026-11-13 | calib | COST | premissas empíricas: LGD 0.327, margem 0.756; limiar 0.550; regret no teste 0.05% | sim |
| [RUN-20261113-calib-COST-02](RUN-20261113-calib-COST-02.md) | 2026-11-13 | calib | COST | config: limiar 0.120, regret 70.80% · estimado: LGD 0.327, margem 0.756, juros dos maus 0.564 · funding 5% | sim |
| [RUN-20261113-train-REF-01](RUN-20261113-train-REF-01.md) | 2026-11-13 | train | REF | candidato | sim |
| [RUN-20261113-train-REF-02](RUN-20261113-train-REF-02.md) | 2026-11-13 | train | REF | champion (v2) | sim |
| [RUN-20261113-train-REF-03](RUN-20261113-train-REF-03.md) | 2026-11-13 | train | REF | candidato | sim |
| [RUN-20261113-calib-COST-03](RUN-20261113-calib-COST-03.md) | 2026-11-13 | calib | COST | config: limiar 0.495, regret 0.88% · estimado: LGD 0.327, margem 0.756, juros dos maus 0.564 · funding 5% | sim |
| [RUN-20261113-sim-S0-01](RUN-20261113-sim-S0-01.md) | 2026-11-13 | sim | S0 | 12 lotes · 0 bloqueados · 71979 linhas pontuadas · diagnóstico esperado none | sim |
| [RUN-20261113-sim-S1-01](RUN-20261113-sim-S1-01.md) | 2026-11-13 | sim | S1 | 12 lotes · 0 bloqueados · 71996 linhas pontuadas · diagnóstico esperado D1 | sim |
| [RUN-20261113-sim-S2-01](RUN-20261113-sim-S2-01.md) | 2026-11-13 | sim | S2 | 12 lotes · 0 bloqueados · 71967 linhas pontuadas · diagnóstico esperado D3 | sim |
| [RUN-20261113-sim-S3-01](RUN-20261113-sim-S3-01.md) | 2026-11-13 | sim | S3 | 12 lotes · 0 bloqueados · 71973 linhas pontuadas · diagnóstico esperado D2 | sim |
| [RUN-20261113-sim-S4-01](RUN-20261113-sim-S4-01.md) | 2026-11-13 | sim | S4 | 12 lotes · 0 bloqueados · 71978 linhas pontuadas · diagnóstico esperado D6 | sim |
| [RUN-20261113-sim-S5-01](RUN-20261113-sim-S5-01.md) | 2026-11-13 | sim | S5 | 60 lotes · 0 bloqueados · 1908945 linhas pontuadas · diagnóstico esperado unknown | sim |
| [RUN-20261113-sim-S1-02](RUN-20261113-sim-S1-02.md) | 2026-11-13 | sim | S1 | 12 lotes · 0 bloqueados · 71996 linhas pontuadas · diagnóstico esperado D1 | sim |
| [RUN-20261113-calib-S0-01](RUN-20261113-calib-S0-01.md) | 2026-11-13 | calib | S0 | FA composto SEV-1+: proposto 0.012 → calibrado 0.002; SEV-2+: proposto 0.000 → calibrado 0.000 | sim |
| [RUN-20261113-monitor-S0-01](RUN-20261113-monitor-S0-01.md) | 2026-11-13 | monitor | S0 | 1º alerta: lote None (atraso None) · camadas — · diagnóstico dominante none (esperado none) | sim |
| [RUN-20261113-monitor-S1-01](RUN-20261113-monitor-S1-01.md) | 2026-11-13 | monitor | S1 | 1º alerta: lote 5 (atraso 2) · camadas L2/L3 · diagnóstico dominante D1 (esperado D1) | sim |
| [RUN-20261113-monitor-S2-01](RUN-20261113-monitor-S2-01.md) | 2026-11-13 | monitor | S2 | 1º alerta: lote 8 (atraso 5) · camadas L4 · diagnóstico dominante D3 (esperado D3) | sim |
| [RUN-20261113-monitor-S3-01](RUN-20261113-monitor-S3-01.md) | 2026-11-13 | monitor | S3 | 1º alerta: lote 7 (atraso 3) · camadas L4 · diagnóstico dominante D2 (esperado D2) | sim |
| [RUN-20261113-monitor-S4-01](RUN-20261113-monitor-S4-01.md) | 2026-11-13 | monitor | S4 | 1º alerta: lote 5 (atraso 0) · camadas L2/L3/L4 · diagnóstico dominante D6 (esperado D6) | sim |
| [RUN-20261113-monitor-S5-01](RUN-20261113-monitor-S5-01.md) | 2026-11-13 | monitor | S5 | 1º alerta: lote 1 (atraso None) · camadas L2/L4 · diagnóstico dominante D1 (esperado unknown) | sim |
| [RUN-20261113-monitor-S5-02](RUN-20261113-monitor-S5-02.md) | 2026-11-13 | monitor | S5 | 1º alerta: lote 1 (atraso None) · camadas L2/L4 · diagnóstico dominante D1 (esperado unknown) | sim |
| [RUN-20261113-sim-S1-03](RUN-20261113-sim-S1-03.md) | 2026-11-13 | sim | S1 | 12 lotes · 0 bloqueados · 71996 linhas pontuadas · diagnóstico esperado D1 | sim |
| [RUN-20261113-monitor-S1-02](RUN-20261113-monitor-S1-02.md) | 2026-11-13 | monitor | S1 | 1º alerta: lote 5 (atraso 2) · camadas L2/L3 · diagnóstico dominante D1 (esperado D1) | sim |
| [RUN-20261115-calib-L4CUT-01](RUN-20261115-calib-L4CUT-01.md) | 2026-11-15 | calib | L4CUT | corte escolhido pela regra nula: 1.25 (máx. nulo 1.103) | sim |
| [RUN-20261115-monitor-S0-01](RUN-20261115-monitor-S0-01.md) | 2026-11-15 | monitor | S0 | 1º alerta: lote None (atraso None) · camadas — · diagnóstico dominante none (esperado none) | sim |
| [RUN-20261115-monitor-S1-01](RUN-20261115-monitor-S1-01.md) | 2026-11-15 | monitor | S1 | 1º alerta: lote 5 (atraso 2) · camadas L2/L3 · diagnóstico dominante D1 (esperado D1) | sim |
| [RUN-20261115-monitor-S2-01](RUN-20261115-monitor-S2-01.md) | 2026-11-15 | monitor | S2 | 1º alerta: lote 8 (atraso 5) · camadas L4 · diagnóstico dominante D3 (esperado D3) | sim |
| [RUN-20261115-monitor-S3-01](RUN-20261115-monitor-S3-01.md) | 2026-11-15 | monitor | S3 | 1º alerta: lote 7 (atraso 3) · camadas L4 · diagnóstico dominante D2 (esperado D2) | sim |
| [RUN-20261115-monitor-S4-01](RUN-20261115-monitor-S4-01.md) | 2026-11-15 | monitor | S4 | 1º alerta: lote 5 (atraso 0) · camadas L2/L3/L4 · diagnóstico dominante D6 (esperado D6) | sim |
| [RUN-20261115-monitor-S5-01](RUN-20261115-monitor-S5-01.md) | 2026-11-15 | monitor | S5 | 1º alerta: lote 1 (atraso None) · camadas L2/L4 · diagnóstico dominante D1 (esperado unknown) | sim |
| [RUN-20261115-monitor-S0-02](RUN-20261115-monitor-S0-02.md) | 2026-11-15 | monitor | S0 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {} | sim |
| [RUN-20261115-monitor-S1-02](RUN-20261115-monitor-S1-02.md) | 2026-11-15 | monitor | S1 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SCORE_DRIFT': 'SEV-1'} | sim |
| [RUN-20261115-monitor-S2-02](RUN-20261115-monitor-S2-02.md) | 2026-11-15 | monitor | S2 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_BAD_RATE_RATIO': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S3-02](RUN-20261115-monitor-S3-02.md) | 2026-11-15 | monitor | S3 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_BAD_RATE_RATIO': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S4-02](RUN-20261115-monitor-S4-02.md) | 2026-11-15 | monitor | S4 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_APPROVAL_SHIFT': 'SEV-1', 'CDM_AUC_DROP': 'SEV-2', 'CDM_BAD_RATE_RATIO': 'SEV-2', 'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SCORE_DRIFT': 'SEV-1', 'CDM_UNIT_BUG_SUSPECTED': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S5-02](RUN-20261115-monitor-S5-02.md) | 2026-11-15 | monitor | S5 | pipeline: 60 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_AUC_DROP': 'SEV-1', 'CDM_BAD_RATE_RATIO': 'SEV-2', 'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SOFT_RULES': 'SEV-1'} | sim |
| [RUN-20261115-monitor-S0-03](RUN-20261115-monitor-S0-03.md) | 2026-11-15 | monitor | S0 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {} | sim |
| [RUN-20261115-monitor-S1-03](RUN-20261115-monitor-S1-03.md) | 2026-11-15 | monitor | S1 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SCORE_DRIFT': 'SEV-1'} | sim |
| [RUN-20261115-monitor-S2-03](RUN-20261115-monitor-S2-03.md) | 2026-11-15 | monitor | S2 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_BAD_RATE_RATIO': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S3-03](RUN-20261115-monitor-S3-03.md) | 2026-11-15 | monitor | S3 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_BAD_RATE_RATIO': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S4-03](RUN-20261115-monitor-S4-03.md) | 2026-11-15 | monitor | S4 | pipeline: 12 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_APPROVAL_SHIFT': 'SEV-1', 'CDM_AUC_DROP': 'SEV-2', 'CDM_BAD_RATE_RATIO': 'SEV-2', 'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SCORE_DRIFT': 'SEV-1', 'CDM_UNIT_BUG_SUSPECTED': 'SEV-2'} | sim |
| [RUN-20261115-monitor-S5-03](RUN-20261115-monitor-S5-03.md) | 2026-11-15 | monitor | S5 | pipeline: 60 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_AUC_DROP': 'SEV-1', 'CDM_BAD_RATE_RATIO': 'SEV-2', 'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SOFT_RULES': 'SEV-1'} | sim |
| [RUN-20261115-response-ALL-01](RUN-20261115-response-ALL-01.md) | 2026-11-15 | response | ALL | política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.942,3; S3: 2.662,1; S4: 0,0 | sim |
| [RUN-20261115-response-ALL-02](RUN-20261115-response-ALL-02.md) | 2026-11-15 | response | ALL | política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.942,3; S3: 2.662,1; S4: 0,0 | sim |
| [RUN-20261115-response-DRILL-01](RUN-20261115-response-DRILL-01.md) | 2026-11-15 | response | DRILL | gate na sombra: aprovado no lote 9 · rollback restaurou o anterior: True · rollback reversível: True | sim |
| [RUN-20261117-gameday-S2-01](RUN-20261117-gameday-S2-01.md) | 2026-11-17 | gameday | S2 | primeiro SEV-1 no lote 8 · primeiro SEV-2 no lote 8 · modo conservador desde o lote 8 | sim |
| [RUN-20261117-response-ALL-01](RUN-20261117-response-ALL-01.md) | 2026-11-17 | response | ALL | política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.942,3; S3: 2.662,1; S4: 0,0 | sim |
| [RUN-20261117-calib-ROBUST-01](RUN-20261117-calib-ROBUST-01.md) | 2026-11-17 | calib | ROBUST | fora da regra na magnitude oficial ou no controle: S2 m=1 | sim |
| [RUN-20261117-fairness-ALL-01](RUN-20261117-fairness-ALL-01.md) | 2026-11-17 | fairness | ALL | S2: custo do limite US$ 205 mil; S3: custo do limite US$ 118 mil | sim |
| [RUN-20261117-response-ALL-02](RUN-20261117-response-ALL-02.md) | 2026-11-17 | response | ALL | política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.737,0; S3: 2.544,1; S4: 0,0 | sim |
| [RUN-20261117-monitor-S5-01](RUN-20261117-monitor-S5-01.md) | 2026-11-17 | monitor | S5 | pipeline: 60 lotes · 0 bloqueados · 0 etapas com falha · alertas {'CDM_AUC_DROP': 'SEV-1', 'CDM_BAD_RATE_RATIO': 'SEV-2', 'CDM_FAIRNESS_GAP': 'SEV-2', 'CDM_FEATURE_DRIFT': 'SEV-2', 'CDM_SOFT_RULES': 'SEV-1'} | sim |
