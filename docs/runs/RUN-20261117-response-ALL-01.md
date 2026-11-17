# RUN-20261117-response-ALL-01

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-17 10:08 |
| Tipo | response |
| Git SHA | `985a49deaba9797ee3d7df4d0a38596cc0044233` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `—` |
| Cenário / seed | ALL / 0 |
| Modelo | champion |
| MLflow | — |

## Métricas

| Métrica | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| modo conservador por valor (política) | 44347.4000 | 13042.2000 | 11781.7000 | 34366.8000 |
| modo conservador por valor, forçado | 44651.0000 | 13042.2000 | 11781.7000 | 28050.5000 |
| não fazer nada | 44347.4000 | 10099.9000 | 9119.7000 | 34366.8000 |
| quarentena e corrigir a fonte | — | — | — | 32648.2000 |
| recalibrar (A5) | 44416.3000 | 10670.6000 | 9993.2000 | 34872.8000 |
| regra por valor sem correção, forçada | 44712.9000 | 10613.1000 | 9651.8000 | 28091.2000 |
| retreinar com gate (A6+GR-5) | 44347.4000 | 10709.0000 | 9119.7000 | 34366.8000 |
| retreinar sem gate | 44238.0000 | 10709.0000 | 9376.5000 | 35834.0000 |
| retreinar sobre o dado com bug | — | — | — | 35568.9000 |
| teto de 14% (descartado, ADR-0019) | 44347.4000 | 8846.0000 | 6167.5000 | 34366.8000 |

## Artefatos

- `docs/evidence/response/compare.json`
- `docs/RESPONSE_EVALUATION.md`

## Veredito

política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.942,3; S3: 2.662,1; S4: 0,0

## Observações

- Valores em US$ mil, somados do ponto de decisão ao último lote.
- Substituído por [RUN-20261117-response-ALL-02](RUN-20261117-response-ALL-02.md): o modo conservador passou a limitar o gap de aprovação entre grupos de `home_ownership` e `emp_length` (ADR-0015); mudam só as linhas do modo conservador.
