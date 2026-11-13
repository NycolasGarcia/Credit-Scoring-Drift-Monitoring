# RUN-20261113-calib-COST-02

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-13 13:09 |
| Tipo | calib |
| Git SHA | `b35d2f90c6d2f134516b0e402a60d603fc5bf04f` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | COST / 42 |
| Modelo | credit-scoring@champion |
| MLflow | — |
| Matriz FP/FN no teste (configured) | {"tn": 6476, "fp": 7180, "fn": 512, "tp": 2009, "fn_loss_total": 2572661.8023845227, "fp_forgone_total": 23805138.565513957, "fn_loss_mean": 5024.730082782271, "fp_forgone_mean": 3315.478908845955, "tp_loss_avoided_total": 13323164.012165928} |
| Matriz FP/FN no teste (estimated) | {"tn": 13642, "fp": 14, "fn": 2507, "tp": 14, "fn_loss_total": 15786780.976469055, "fp_forgone_total": 106884.8147420208, "fn_loss_mean": 6297.080565005606, "fp_forgone_mean": 7634.6296244300565, "tp_loss_avoided_total": 109044.83808139624} |
| Sensibilidade ao custo de funding (teste, caixa realizado) | [{"funding_rate": 0.0, "realized_optimal_threshold": 0.555, "approval_rate": 0.9997, "value_per_app": 2053.5184, "value_approve_all": 2053.3362}, {"funding_rate": 0.03, "realized_optimal_threshold": 0.435, "approval_rate": 0.991, "value_per_app": 1375.0613, "value_approve_all": 1372.52}, {"funding_rate": 0.05, "realized_optimal_threshold": 0.435, "approval_rate": 0.991, "value_per_app": 926.9769, "value_approve_all": 918.6425}, {"funding_rate": 0.08, "realized_optimal_threshold": 0.4, "approval_rate": 0.9818, "value_per_app": 257.1546, "value_approve_all": 237.8262}, {"funding_rate": 0.1, "realized_optimal_threshold": 0.02, "approval_rate": 0.004, "value_per_app": -2.3674, "value_approve_all": -216.0513}] |

## Métricas

| Métrica | configured | estimated | premissas (train) |
|---|---|---|---|
| bad_interest_realization | 0.0000 | 0.5637 | 0.5637 |
| curve_pearson | -0.8545 | 0.9986 | — |
| funding_rate | 0.0500 | 0.0500 | — |
| interest_realization_median | — | — | 0.9256 |
| lgd | 0.6000 | 0.3272 | 0.3272 |
| loss_rate_median | — | — | 0.3553 |
| loss_rate_p25 | — | — | 0.1079 |
| loss_rate_p75 | — | — | 0.5843 |
| margin_realization | 0.5000 | 0.7560 | 0.7560 |
| n_bad | — | — | 11773.0000 |
| n_good | — | — | 63717.0000 |
| realized_optimal_threshold | 0.4350 | 0.4350 | — |
| realized_value_at_chosen | 270.6871 | 918.7760 | — |
| realized_value_at_optimal | 926.9769 | 926.9769 | — |
| regret_pct | 70.7989 | 0.8847 | — |
| threshold | 0.1200 | 0.4950 | — |

## Artefatos

- `docs/evidence/models/cost_validation.json`

## Veredito

config: limiar 0.120, regret 70.80% · estimado: LGD 0.327, margem 0.756, juros dos maus 0.564 · funding 5%

## Observações

