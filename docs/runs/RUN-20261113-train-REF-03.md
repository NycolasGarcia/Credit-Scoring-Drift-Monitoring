# RUN-20261113-train-REF-03

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-13 13:10 |
| Tipo | train |
| Git SHA | `670a46aa6904a0a0c99bfbe8b26c62efd38bbef2` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | REF / 42 |
| Modelo | xgboost |
| MLflow | training / 010b71e8eabe4ef9ab0df0b0c8dbe675 |
| Calibração | isotonic |
| Brier calib_select | {"raw": 0.12272289395332336, "sigmoid": 0.1231256342329431, "isotonic": 0.12288724808812335} |
| PSI do score (test → OOT) | {"oot_2014": 0.0722, "oot_2015": 0.238} |

## Métricas

| Métrica | cv_train | test_raw | test | oot_2014 | oot_2015 |
|---|---|---|---|---|---|
| auc | 0.7009 | 0.6995 | 0.6979 | 0.6903 | 0.6928 |
| auc_std | 0.0068 | — | — | — | — |
| bad_rate_expected | — | 0.1558 | 0.1546 | 0.1302 | 0.1119 |
| bad_rate_observed | — | 0.1558 | 0.1558 | 0.1463 | 0.1488 |
| brier | — | 0.1227 | 0.1229 | 0.1179 | 0.1207 |
| gini | — | 0.3989 | 0.3957 | 0.3805 | 0.3856 |
| ks | — | 0.3067 | 0.2998 | 0.2797 | 0.2828 |
| log_loss | — | 0.3992 | 0.4033 | 0.3918 | 0.4001 |
| n | — | 16177 | 16177 | 175509 | 282787 |
| pr_auc | — | 0.2904 | 0.2822 | 0.2620 | 0.2646 |

## Artefatos

- `mlflow: model`

## Veredito

candidato

## Observações

