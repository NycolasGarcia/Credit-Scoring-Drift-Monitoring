# Comparação de respostas à degradação

> Gerado por `make respond-compare` (`src/response/docs.py`). Não editar à mão.

RUN: [RUN-20261115-response-ALL-01](runs/RUN-20261115-response-ALL-01.md).

Cada estratégia decide os lotes a partir do ponto de decisão, o primeiro lote em que a matriz de resposta pede mais do que registrar. O valor usa o desfecho realizado da simulação e a economia do [ADR-0016](adr/0016-empirical-cost-threshold.md): bom aprovado rende o ganho, mau aprovado custa a perda, recusa e revisão valem 0 no lote. Recalibrar e retreinar usam só o que é observável no ponto de decisão (GR-7, GR-8) e valem a partir do lote seguinte. Decisões em [ADR-0012](adr/0012-guardrails-conservative-mode.md) e [ADR-0013](adr/0013-retraining-gate-rollback.md).


## S1

Ponto de decisão: lote 5 (7 lotes avaliados). Regra da matriz: **P09** — Drift benigno ou só de entrada (L3 estável) (ações A0).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` -0.0054 (limite 0.0) falhou; `auc_loss_reference` 0.0038 (limite 0.01) ok; `calibration_gap_pp` 0.2487 (limite 1.0) ok; `fairness_gap_increase_pp` 0.0827 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| modo conservador por valor (política) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| modo conservador por valor, forçado | 44.651,0 | 303,6 | 44.347,4 | 1063 | 95,4% | 3,2% | 18,5% |
| regra por valor sem correção, forçada | 44.712,9 | 365,5 | 44.347,4 | 1065 | 95,9% | 2,7% | 18,6% |
| teto de 14% (descartado, ADR-0019) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| recalibrar (A5) | 44.416,3 | 69,0 | 44.416,3 | 1058 | 98,7% | 0,0% | 19,2% |
| retreinar com gate (A6+GR-5) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| retreinar sem gate | 44.238,0 | -109,3 | 44.238,0 | 1053 | 97,5% | 0,0% | 18,8% |

## S2

Ponto de decisão: lote 8 (4 lotes avaliados). Regra da matriz: **P03** — Concept drift confirmado com rótulo maduro (ações A4, A6, A3, A7).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` 0.0054 (limite 0.0) ok; `auc_loss_reference` 0.0058 (limite 0.01) ok; `calibration_gap_pp` 1.5532 (limite 1.0) falhou; `fairness_gap_increase_pp` 1.2810 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 10.099,9 | 0,0 | 10.099,9 | 421 | 99,8% | 0,0% | 21,0% |
| modo conservador por valor (política) | 13.042,2 | 2.942,3 | 10.099,9 | 544 | 82,4% | 17,4% | 18,0% |
| modo conservador por valor, forçado | 13.042,2 | 2.942,3 | 10.099,9 | 544 | 82,4% | 17,4% | 18,0% |
| regra por valor sem correção, forçada | 10.613,1 | 513,2 | 10.099,9 | 442 | 96,8% | 3,0% | 20,8% |
| teto de 14% (descartado, ADR-0019) | 8.846,0 | -1.253,9 | 10.099,9 | 369 | 72,2% | 27,6% | 14,1% |
| recalibrar (A5) | 10.670,6 | 570,6 | 10.670,6 | 445 | 98,3% | 0,0% | 20,4% |
| retreinar com gate (A6+GR-5) | 10.099,9 | 0,0 | 10.099,9 | 421 | 99,8% | 0,0% | 21,0% |
| retreinar sem gate | 10.709,0 | 609,1 | 10.709,0 | 446 | 98,3% | 0,0% | 20,4% |

## S3

Ponto de decisão: lote 7 (5 lotes avaliados). Regra da matriz: **P05** — Prior shift relevante, ranking preservado (ações A4, A5, A3).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` -0.0023 (limite 0.0) falhou; `auc_loss_reference` 0.0038 (limite 0.01) ok; `calibration_gap_pp` 5.1968 (limite 1.0) falhou; `fairness_gap_increase_pp` 0.1795 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 9.119,7 | 0,0 | 9.119,7 | 304 | 99,8% | 0,0% | 22,7% |
| modo conservador por valor (política) | 11.781,7 | 2.662,1 | 9.119,7 | 393 | 73,2% | 26,6% | 19,4% |
| modo conservador por valor, forçado | 11.781,7 | 2.662,1 | 9.119,7 | 393 | 73,2% | 26,6% | 19,4% |
| regra por valor sem correção, forçada | 9.651,8 | 532,2 | 9.119,7 | 322 | 97,0% | 2,7% | 22,6% |
| teto de 14% (descartado, ADR-0019) | 6.167,5 | -2.952,2 | 9.119,7 | 206 | 62,9% | 36,9% | 15,0% |
| recalibrar (A5) | 9.993,2 | 873,5 | 9.993,2 | 333 | 96,7% | 0,0% | 21,6% |
| retreinar com gate (A6+GR-5) | 9.119,7 | 0,0 | 9.119,7 | 304 | 99,8% | 0,0% | 22,7% |
| retreinar sem gate | 9.376,5 | 256,8 | 9.376,5 | 313 | 99,5% | 0,0% | 22,6% |

## S4

Ponto de decisão: lote 5 (7 lotes avaliados). Regra da matriz: **P02** — Suspeita de bug upstream (ações A2, A1, A3).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` -0.0003 (limite 0.0) falhou; `auc_loss_reference` 0.0027 (limite 0.01) ok; `calibration_gap_pp` 0.5973 (limite 1.0) ok; `fairness_gap_increase_pp` -0.0723 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 34.366,8 | 0,0 | 34.366,8 | 818 | 93,7% | 0,0% | 14,7% |
| modo conservador por valor (política) | 34.366,8 | 0,0 | 34.366,8 | 818 | 93,7% | 0,0% | 14,7% |
| modo conservador por valor, forçado | 28.050,5 | -6.316,2 | 34.366,8 | 668 | 70,9% | 22,9% | 15,5% |
| regra por valor sem correção, forçada | 28.091,2 | -6.275,5 | 34.366,8 | 669 | 71,0% | 22,7% | 15,5% |
| teto de 14% (descartado, ADR-0019) | 34.366,8 | 0,0 | 34.366,8 | 818 | 93,7% | 0,0% | 14,7% |
| recalibrar (A5) | 34.872,8 | 506,1 | 34.872,8 | 831 | 94,3% | 0,0% | 14,8% |
| retreinar com gate (A6+GR-5) | 34.366,8 | 0,0 | 34.366,8 | 818 | 93,7% | 0,0% | 14,7% |
| retreinar sem gate | 35.834,0 | 1.467,2 | 35.834,0 | 853 | 95,2% | 0,0% | 14,8% |
| quarentena e corrigir a fonte | 32.648,2 | -1.718,6 | 38.373,1 | 778 | 85,5% | 14,3% | 15,6% |
| retreinar sobre o dado com bug | 35.568,9 | 1.202,1 | 35.568,9 | 847 | 95,5% | 0,0% | 14,9% |

## Leitura

**A resposta certa depende do diagnóstico, e a matriz acerta qual é.** Valores contra "não fazer nada", com a revisão tratada como perda, salvo indicação.

- **D1, choque econômico (S1).**
  - **A política não age** (regra P09, só registrar), e é o certo: o modelo continua calibrado.
  - **Forçar respostas não compensa:** retreinar sem gate perderia US$ 109 mil, e recalibrar dá +US$ 69 mil, o que é ruído.
- **D3, concept drift (S2).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,94 mi**, com 17,4% das propostas em revisão.
  - **De onde vem o ganho:** a regra por valor sem correção de risco rende +US$ 0,51 mi. Portanto, cerca de 83% do ganho vem da correção pela razão observado/esperado.
  - **Alternativas de modelo:** recalibrar dá +US$ 0,57 mi. O challenger renderia +US$ 0,61 mi, mas o gate o reprovou por 1,55 p.p. de descalibração.
- **D2, prior shift (S3).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,66 mi**, e a recalibração, sozinha, **+US$ 0,87 mi**.
  - **Combinação:** a matriz recomenda as duas (A4 automático e A5 humano). O efeito combinado não foi simulado.
- **D6, bug de unidade (S4).**
  - **A política retém o lote e manda corrigir a fonte.**
  - **Custo da quarentena:** depende do que acontece com a fila. Se ela se perde, a quarentena custa US$ 1,72 mi; se é decidida depois do conserto, rende **+US$ 4,01 mi** contra decidir sobre o dado quebrado.
  - **A pior resposta seria o modo conservador:** forçado sobre o bug, perderia US$ 6,3 mi, porque o bug faz o modelo enxergar risco onde não há.

**O teto de 14% foi descartado com evidência** ([ADR-0019](adr/0019-conservative-mode-by-value.md)). Ele recusa empréstimos que continuam lucrativos: −US$ 1,25 mi no S2 e −US$ 2,95 mi no S3. Na carteira já aprovada pelo credor, o corte certo é o de valor esperado negativo, não um teto de bad rate.

**O gate de promoção é conservador por desenho.**
- **Rejeitou os quatro challengers do ponto de decisão.**
- **No S1, evitou uma perda de US$ 109 mil.**
- **Nos outros, deixou valor na mesa:** +US$ 0,61 mi no S2, +US$ 0,26 mi no S3 e +US$ 1,47 mi no S4.
- **No ponto de decisão quase não há rótulo maduro do regime novo** (atraso de 3 lotes), então retreinar cedo é uma aposta. O gate a recusa enquanto o challenger não prova calibração.

**Retreinar sobre o bug parece bom, e por isso é perigoso.** Enquanto o bug persiste, o challenger treinado no dado quebrado rende +US$ 1,2 mi, porque aprende a descontar a renda corrompida. É exatamente o modo como o retreino esconde um defeito de dado: quando a fonte for corrigida, esse modelo estará calibrado para um dado que não existe mais. Este cenário não mede esse segundo momento. A regra GR-7 e a precedência do D6 existem para não chegar lá.

**Premissas que limitam a leitura:**
- **Horizonte curto:** de 4 a 7 lotes após o ponto de decisão.
- **Custo da equipe de revisão não modelado.**
- **Revisão em dois extremos:** perdida, ou decidida depois como o champion decidiria. No modo por valor, decidir depois "como o champion" anula o ganho; o ganho exige que a revisão confirme a recusa dos casos de valor negativo.
- **Cenários simulados:** os desfechos vêm do oráculo do [ADR-0017](adr/0017-scenario-simulator.md).
