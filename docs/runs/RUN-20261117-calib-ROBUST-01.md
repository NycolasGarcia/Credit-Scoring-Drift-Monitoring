# RUN-20261117-calib-ROBUST-01

> Gerado por `src/reporting/run_record.py`. Não editar números à mão.

| Campo | Valor |
|---|---|
| Data | 2026-11-17 13:02 |
| Tipo | calib |
| Git SHA | `b43378b9cc5c3f85035fda300296fb6bc1743a45` |
| Árvore limpa | sim |
| Hash dos dados de entrada | `901725d664ea` |
| Cenário / seed | ROBUST / 0 |
| Modelo | champion |
| MLflow | — |
| seeds | [301, 302, 303, 304, 305] |
| magnitudes | [0.25, 0.5, 1.0, 1.5] |

## Métricas

| Métrica | S0 m=— | S1 m=0,25 | S1 m=0,5 | S1 m=1 | S1 m=1,5 | S2 m=0,25 | S2 m=0,5 | S2 m=1 | S2 m=1,5 | S3 m=0,25 | S3 m=0,5 | S3 m=1 | S3 m=1,5 | S4 m=0,25 | S4 m=0,5 | S4 m=1 | S4 m=1,5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SEV-2 antes do início | 0/60 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/20 | 0/20 | 0/20 | 0/20 | 0/25 | 0/25 | 0/25 | 0/25 |
| detectadas SEV-2+ | 0/5 | 0/5 | 0/5 | 5/5 | 5/5 | 0/5 | 0/5 | 5/5 | 5/5 | 0/5 | 3/5 | 5/5 | 5/5 | 0/5 | 0/5 | 5/5 | 5/5 |
| diagnóstico certo | 0/0 | 0/0 | 25/25 | 35/35 | 40/40 | 0/0 | 0/1 | 19/20 | 25/25 | 0/0 | 18/18 | 25/25 | 25/25 | 0/1 | 35/35 | 35/35 | 34/34 |

## Artefatos

- `docs/evidence/drift/robustness.json`
- `docs/ROBUSTNESS.md`

## Veredito

fora da regra na magnitude oficial ou no controle: S2 m=1

## Observações
- Substituído por [RUN-20261117-calib-ROBUST-02](RUN-20261117-calib-ROBUST-02.md): o modo conservador passou a limitar o gap de aprovação entre grupos (ADR-0015). Detecção e respostas de modelo idênticas; mudam só as linhas do modo conservador.
