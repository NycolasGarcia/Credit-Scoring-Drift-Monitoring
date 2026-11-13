# RUN-20261112-train-REF-02

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-12 22:27 |
| Tipo | train |
| Git SHA | `b8b3a225a54b6199245c49ca4f94838af3c03d61` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `8f438ed3cf939baf2b30532e6382cb213908f6fc3f2178c9ac03f09f3aa65396` |
| Cenário / seed | REF / 42 |
| Modelo | logreg |
| MLflow | training / 500f5b3fcc4345d59019dfd1097689a0 |
| Calibração | sigmoid |
| Brier calib_select | {"raw": 0.1229363276446248, "sigmoid": 0.12293617042555145, "isotonic": 0.12319616052146418} |
| PSI do score (test → OOT) | {"oot_2014": 0.0734, "oot_2015": 0.2257} |
| Limiar (valor esperado) | 0.3300 |
| Limiar (F1) | 0.1950 |
| Decisão no test | {"threshold": {"threshold": 0.33, "approval_rate": 0.943129133955616, "bad_rate_approved": 0.14275414563806776, "value_per_app": 445.3303739877604}, "threshold_f1": {"threshold": 0.195, "approval_rate": 0.7146566112381777, "bad_rate_approved": 0.10500821728224202, "value_per_app": 411.6418396488843}} |

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

champion (v1)

## Observações

- *(humano, 2026-11-12)* Calibração neutra: Brier no teste 0,12253362 (pré) contra 0,12253509 (pós). O portão PROPOSTO "Brier pós ≤ pré" falha por 1,5×10⁻⁶ (ruído). A LogReg já sai calibrada (esperado 15,50% × observado 15,58%). Ver ADR-0006.
- *(humano, 2026-11-12)* Degradação natural fora do tempo: observado/esperado 1,113 (OOT 2014) e 1,287 (OOT 2015), com AUC estável. É perda de calibração com o ranking preservado; detalhe em `notebooks/02_modelagem.ipynb`.

