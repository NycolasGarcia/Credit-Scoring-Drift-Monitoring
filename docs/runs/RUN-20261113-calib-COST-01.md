# RUN-20261113-calib-COST-01

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-13 11:07 |
| Tipo | calib |
| Git SHA | `78909fc707398220f16eddcc9fdd7f94bbdbb149` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | COST / 42 |
| Modelo | credit-scoring@champion |
| MLflow | — |
| Matriz FP/FN no teste (proposed) | {"tn": 13079, "fp": 577, "fn": 2178, "tp": 343, "fn_loss_total": 10936578.813831389, "fp_forgone_total": 5003296.622245146, "fn_loss_mean": 5021.386048591087, "fp_forgone_mean": 8671.224648605106, "tp_loss_avoided_total": 2313923.1267349795} |
| Matriz FP/FN no teste (empirical) | {"tn": 13652, "fp": 4, "fn": 2517, "tp": 4, "fn_loss_total": 13241091.338433553, "fp_forgone_total": 24482.4993748732, "fn_loss_mean": 5260.6640200371685, "fp_forgone_mean": 6120.6248437183, "tp_loss_avoided_total": 9410.6021328145} |
| Sensibilidade ao custo de funding (teste, caixa realizado) | [{"funding_rate": 0.0, "realized_optimal_threshold": 0.555, "approval_rate": 0.9997, "value_per_app": 2053.5184, "value_approve_all": 2053.3362}, {"funding_rate": 0.03, "realized_optimal_threshold": 0.435, "approval_rate": 0.991, "value_per_app": 1375.0613, "value_approve_all": 1372.52}, {"funding_rate": 0.05, "realized_optimal_threshold": 0.435, "approval_rate": 0.991, "value_per_app": 926.9769, "value_approve_all": 918.6425}, {"funding_rate": 0.08, "realized_optimal_threshold": 0.4, "approval_rate": 0.9818, "value_per_app": 257.1546, "value_approve_all": 237.8262}, {"funding_rate": 0.1, "realized_optimal_threshold": 0.02, "approval_rate": 0.004, "value_per_app": -2.3674, "value_approve_all": -216.0513}] |

## Métricas

| Métrica | proposed | empirical | premissas (train) |
|---|---|---|---|
| curve_pearson | 0.9209 | 0.9992 | — |
| interest_realization_median | — | — | 0.9256 |
| lgd | 0.6000 | 0.3272 | 0.3272 |
| loss_rate_median | — | — | 0.3553 |
| loss_rate_p25 | — | — | 0.1079 |
| loss_rate_p75 | — | — | 0.5843 |
| margin_realization | 0.5000 | 0.7560 | 0.7560 |
| n_bad | — | — | 11773.0000 |
| n_good | — | — | 63717.0000 |
| realized_optimal_threshold | 0.5550 | 0.5550 | — |
| realized_value_at_chosen | 1887.0895 | 2052.4046 | — |
| realized_value_at_optimal | 2053.5184 | 2053.5184 | — |
| regret_pct | 8.1046 | 0.0542 | — |
| threshold | 0.3300 | 0.5500 | — |

## Artefatos

- `docs/evidence/models/cost_validation.json`

## Veredito

premissas empíricas: LGD 0.327, margem 0.756; limiar 0.550; regret no teste 0.05%

## Observações

