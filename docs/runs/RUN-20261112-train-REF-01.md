# RUN-20261112-train-REF-01

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-12 22:27 |
| Tipo | train |
| Git SHA | `b8b3a225a54b6199245c49ca4f94838af3c03d61` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | REF / 42 |
| Modelo | dummy |
| MLflow | training / 5f320f4d5fcf4a15abd52e712fa180b8 |
| Calibração | none |
| Brier calib_select | {} |
| PSI do score (test → OOT) | {"oot_2014": 0.0, "oot_2015": 0.0} |

## Métricas

| Métrica | cv_train | test_raw | test | oot_2014 | oot_2015 |
|---|---|---|---|---|---|
| auc | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 |
| auc_std | 0.0000 | — | — | — | — |
| bad_rate_expected | — | 0.1560 | 0.1560 | 0.1560 | 0.1560 |
| bad_rate_observed | — | 0.1558 | 0.1558 | 0.1463 | 0.1488 |
| brier | — | 0.1316 | 0.1316 | 0.1250 | 0.1267 |
| gini | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| ks | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| log_loss | — | 0.4327 | 0.4327 | 0.4166 | 0.4209 |
| n | — | 16177 | 16177 | 175509 | 282787 |
| pr_auc | — | 0.1558 | 0.1558 | 0.1463 | 0.1488 |

## Artefatos

- `mlflow: model`

## Veredito

candidato

## Observações

