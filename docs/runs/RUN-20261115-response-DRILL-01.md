# RUN-20261115-response-DRILL-01

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-15 19:14 |
| Tipo | response |
| Git SHA | `01f11bcd95b51e465d857e77593de14ee9314445` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `—` |
| Cenário / seed | DRILL / 0 |
| Modelo | credit-scoring-drill (ensaio) |
| MLflow | experimento `response` |
| cenário | S2 |
| challenger treinado no lote | 8 |

## Métricas

| Métrica | lote 9 | lote 10 | lote 11 |
|---|---|---|---|
| auc_challenger | 0.7284 | 0.7139 | 0.7241 |
| auc_champion | 0.7230 | 0.7088 | 0.7187 |
| ratio_challenger | 1.1343 | 1.0668 | 1.1482 |
| ratio_champion | 1.3594 | 1.2768 | 1.3722 |
| rows | 5998.0000 | 5998.0000 | 5998.0000 |

## Artefatos

- `docs/evidence/response/shadow_drill.json`

## Veredito

gate na sombra: aprovado no lote 9 · rollback restaurou o anterior: True · rollback reversível: True

## Observações

