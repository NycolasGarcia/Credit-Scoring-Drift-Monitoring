# Limiares do monitoramento

> Gerado por `make drift-docs` (`src/monitoring/docs.py`). Não editar à mão.

Fonte: `config/monitoring/thresholds.yaml` (versão 1) e `docs/evidence/drift/calibration_S0.json`. Meta de falso alarme por lote no controle: SEV-1+ ≤ 5.0%, SEV-2+ ≤ 0.0% (PROPOSTO). Feature importante = top-10 da importância por permutação.

## Limiares vigentes

| Id | Sinal | Camada | Direção | SEV-1 | SEV-2 | SEV-3 | Status | RUN |
|---|---|---|---|---|---|---|---|---|
| TH-FEAT-PSI | `feature_psi` | L2 | higher_is_worse | 0.100 | 0.250 | ≥ 3 top-k | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |
| TH-SCORE-PSI | `score_psi` | L3 | higher_is_worse | 0.100 | 0.250 | — | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |
| TH-APPROVAL | `approval_delta_pp` | L3 | two_sided | 3.000 | 7.000 | 12.000 | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |
| TH-BADRATE | `bad_rate_ratio` | L4 | symmetric_ratio | 1.200 | 1.500 | 2.000 | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |
| TH-AUC | `auc_drop` | L4 | higher_is_worse | 0.025 | 0.050 | 0.100 | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |
| TH-SEGMENT-GAP | `segment_gap` | L4 | higher_is_worse | 0.500 | — | — | CALIBRADO | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) |

## Calibração no controle (S0)

RUN: [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md) · 500 réplicas A/A de 6000 propostas sorteadas do holdout.

| Sinal | Mediana nula | q95 | q99 | Máx. nulo | SEV-1 proposto | FA no proposto | SEV-1 calibrado | SEV-2 calibrado |
|---|---|---|---|---|---|---|---|---|
| `feature_psi` | 0.0031 | 0.0043 | 0.0050 | 0.0051 | 0.100 | 0.0% | 0.100 | 0.250 |
| `score_psi` | 0.0015 | 0.0029 | 0.0035 | 0.0054 | 0.100 | 0.0% | 0.100 | 0.250 |
| `approval_delta_pp` | 0.0392 | 0.0947 | 0.1225 | 0.1608 | 3.000 | 0.0% | 3.000 | 7.000 |
| `bad_rate_ratio` | 1.0196 | 1.0590 | 1.0753 | 1.0905 | 1.200 | 0.0% | 1.200 | 1.500 |
| `auc_drop` | 0.0037 | 0.0168 | 0.0204 | 0.0278 | 0.020 | 1.2% | 0.025 | 0.050 |
| `segment_gap` | 0.2812 | 0.3770 | 0.4315 | 0.5373 | 0.500 | 0.2% | 0.500 | — |

Falso alarme composto (qualquer sinal): SEV-1+ 1.2% com os valores propostos → 0.2% calibrado; SEV-2+ 0.0%.

## Racional

- **TH-FEAT-PSI** — Convenção de mercado de crédito (NV-9); bins fixos da referência.
- **TH-SCORE-PSI** — Mesma convenção do PSI de feature, aplicada à distribuição do score.
- **TH-APPROVAL** — Variação absoluta da taxa de aprovação vs. referência, em pontos percentuais.
- **TH-BADRATE** — Bad rate observado / esperado (média do score) na coorte com rótulo maduro.
- **TH-AUC** — Queda de AUC da coorte madura vs. AUC de referência (teste 2013).
- **TH-SEGMENT-GAP** — Amplitude, em logit, do descolamento observado/esperado entre quintis de uma feature top-k. Não gera alerta sozinho; separa concept drift (descolamento concentrado num segmento, D3) de prior shift (descolamento uniforme, D2).

## Assinatura de bug de unidade (D6)

Cauda abaixo do percentil 1 da referência; suspeita quando o excesso na cauda passa de 5.0%; confirmada quando corrigir a cauda por um fator em [12.0, 52.0, 100.0, 1000.0] reduz o PSI a no máximo 50.0% do original (PROPOSTO).

## Leitura

- **A convenção de mercado é conservadora para estes lotes.** Num lote de 6.000 propostas sem drift, o maior PSI de feature foi 0,005 e o do score 0,005, cerca de 20× abaixo do corte de 0,10. A regra de calibração mantém a convenção como piso: um corte menor detectaria o choque econômico (S1) mais cedo, mas também alertaria para mudanças pequenas que não afetam a decisão. Drift não é degradação (§8.1).
- **A queda de AUC é o único sinal com ruído relevante.** A AUC de 6.000 propostas oscila: o corte proposto de 0,02 dava 1,2% de falso alarme. Pela regra de Bonferroni, sobe para 0,025.
- **O bad rate observado no holdout fica ~2% acima do esperado** (mediana nula de 1,02). É a calibração do champion na população de 2013, bem abaixo do corte de 1,2.
- **O descolamento por segmento tem ruído alto** (mediana 0,28 em logit). Por isso ele não gera alerta sozinho: só decide entre D3 e D2 quando o bad rate já alertou. O corte de 0,5 deixa 0,2% de falso diagnóstico no controle.
- **A meta de falso alarme (5% SEV-1, 0% SEV-2) continua PROPOSTO:** é decisão do autor (§15). Com os cortes calibrados, o controle fica em 0,2% e 0%.
