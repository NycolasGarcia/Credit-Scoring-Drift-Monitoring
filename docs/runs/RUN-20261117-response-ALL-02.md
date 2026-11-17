# RUN-20261117-response-ALL-02

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-17 16:41 |
| Tipo | response |
| Git SHA | `4e12fd1f9a67a115c3ccf09829d6d59638894afa` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `—` |
| Cenário / seed | ALL / 0 |
| Modelo | champion |
| MLflow | — |

## Métricas

| Métrica | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| modo conservador por valor (política) | 44347.4000 | 12836.9000 | 11663.7000 | 34366.8000 |
| modo conservador por valor, forçado | 44640.1000 | 12836.9000 | 11663.7000 | 28032.3000 |
| não fazer nada | 44347.4000 | 10099.9000 | 9119.7000 | 34366.8000 |
| quarentena e corrigir a fonte | — | — | — | 32648.2000 |
| recalibrar (A5) | 44416.3000 | 10670.6000 | 9993.2000 | 34872.8000 |
| regra por valor sem correção, forçada | 44656.0000 | 10517.3000 | 9558.7000 | 28087.0000 |
| retreinar com gate (A6+GR-5) | 44347.4000 | 10709.0000 | 9119.7000 | 34366.8000 |
| retreinar sem gate | 44238.0000 | 10709.0000 | 9376.5000 | 35834.0000 |
| retreinar sobre o dado com bug | — | — | — | 35568.9000 |
| teto de 14% (descartado, ADR-0019) | 44347.4000 | 8846.0000 | 6167.5000 | 34366.8000 |

## Artefatos

- `docs/evidence/response/compare.json`
- `docs/RESPONSE_EVALUATION.md`

## Veredito

política (modo conservador por valor) vs. não fazer nada, US$ mil — S1: 0,0; S2: 2.737,0; S3: 2.544,1; S4: 0,0

## Observações

- Valores em US$ mil, somados do ponto de decisão ao último lote.
