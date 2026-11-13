# RUN-20261113-train-REF-02

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-13 13:10 |
| Tipo | train |
| Git SHA | `670a46aa6904a0a0c99bfbe8b26c62efd38bbef2` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | REF / 42 |
| Modelo | logreg |
| MLflow | training / ab3e3345aeef40029421a0b56c8bfabd |
| Calibração | sigmoid |
| Brier calib_select | {"raw": 0.1229363276446248, "sigmoid": 0.12293617042555145, "isotonic": 0.12319616052146418} |
| PSI do score (test → OOT) | {"oot_2014": 0.0734, "oot_2015": 0.2257} |
| Limiar (valor esperado) | 0.4950 |
| Limiar (F1) | 0.1950 |
| Decisão no test | {"threshold": {"threshold": 0.495, "approval_rate": 0.9982691475551709, "bad_rate_approved": 0.15524181063842962, "value_per_app": 942.1732188610811}, "threshold_f1": {"threshold": 0.195, "approval_rate": 0.7146566112381777, "bad_rate_approved": 0.10500821728224202, "value_per_app": 546.9037435667616}} |

## Métricas

| Métrica | cv_train | test_raw | test | oot_2014 | oot_2015 |
|---|---|---|---|---|---|
| auc | 0.6989 | 0.7001 | 0.7001 | 0.6907 | 0.6954 |
| auc_std | 0.0064 | — | — | — | — |
| bad_rate_expected | — | 0.1562 | 0.1550 | 0.1315 | 0.1156 |
| bad_rate_observed | — | 0.1558 | 0.1558 | 0.1463 | 0.1488 |
| brier | — | 0.1225 | 0.1225 | 0.1178 | 0.1204 |
| gini | — | 0.4002 | 0.4002 | 0.3814 | 0.3907 |
| ks | — | 0.3032 | 0.3032 | 0.2801 | 0.2853 |
| log_loss | — | 0.3990 | 0.3990 | 0.3883 | 0.3953 |
| n | — | 16177 | 16177 | 175509 | 282787 |
| pr_auc | — | 0.2931 | 0.2931 | 0.2691 | 0.2720 |

## Artefatos

- `mlflow: model`
- `models/reference_profile.json`

## Veredito

champion (v2)

## Observações

