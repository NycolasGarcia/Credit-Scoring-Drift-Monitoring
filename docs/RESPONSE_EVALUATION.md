# Comparação de respostas à degradação

> Gerado por `make respond-compare` (`src/response/docs.py`). Não editar à mão.

RUN: [RUN-20261117-response-ALL-02](runs/RUN-20261117-response-ALL-02.md).

Cada estratégia decide os lotes a partir do ponto de decisão, o primeiro lote em que a matriz de resposta pede mais do que registrar. O valor usa o desfecho realizado da simulação e a economia do [ADR-0016](adr/0016-empirical-cost-threshold.md): bom aprovado rende o ganho, mau aprovado custa a perda, recusa e revisão valem 0 no lote. Recalibrar e retreinar usam só o que é observável no ponto de decisão (GR-7, GR-8) e valem a partir do lote seguinte. Decisões em [ADR-0012](adr/0012-guardrails-conservative-mode.md) e [ADR-0013](adr/0013-retraining-gate-rollback.md).


## S1

Ponto de decisão: lote 5 (7 lotes avaliados). Regra da matriz: **P09** — Drift benigno ou só de entrada (L3 estável) (ações A0).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` -0.0054 (limite 0.0) falhou; `auc_loss_reference` 0.0038 (limite 0.01) ok; `calibration_gap_pp` 0.2487 (limite 1.0) ok; `fairness_gap_increase_pp` 0.0827 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| modo conservador por valor (política) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| modo conservador por valor, forçado | 44.640,1 | 292,7 | 44.347,4 | 1063 | 95,9% | 2,7% | 18,6% |
| regra por valor sem correção, forçada | 44.656,0 | 308,6 | 44.347,4 | 1063 | 96,3% | 2,2% | 18,7% |
| teto de 14% (descartado, ADR-0019) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| recalibrar (A5) | 44.416,3 | 69,0 | 44.416,3 | 1058 | 98,7% | 0,0% | 19,2% |
| retreinar com gate (A6+GR-5) | 44.347,4 | 0,0 | 44.347,4 | 1056 | 98,6% | 0,0% | 19,1% |
| retreinar sem gate | 44.238,0 | -109,3 | 44.238,0 | 1053 | 97,5% | 0,0% | 18,8% |

## S2

Ponto de decisão: lote 8 (4 lotes avaliados). Regra da matriz: **P03** — Concept drift confirmado com rótulo maduro (ações A4, A6, A3, A7).

Gate do challenger (GR-5): **aprovado** — `auc_gain_recent` 0.0054 (limite 0.0) ok; `auc_loss_reference` 0.0058 (limite 0.01) ok; `calibration_gap_pp` 1.5532 (limite 4.656467498050451) ok; `fairness_gap_increase_pp` 1.2810 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 10.099,9 | 0,0 | 10.099,9 | 421 | 99,8% | 0,0% | 21,0% |
| modo conservador por valor (política) | 12.836,9 | 2.737,0 | 11.174,5 | 535 | 86,2% | 10,9% | 18,4% |
| modo conservador por valor, forçado | 12.836,9 | 2.737,0 | 11.174,5 | 535 | 86,2% | 10,9% | 18,4% |
| regra por valor sem correção, forçada | 10.517,3 | 417,4 | 10.099,9 | 438 | 97,2% | 2,6% | 20,8% |
| teto de 14% (descartado, ADR-0019) | 8.846,0 | -1.253,9 | 10.099,9 | 369 | 72,2% | 27,6% | 14,1% |
| recalibrar (A5) | 10.670,6 | 570,6 | 10.670,6 | 445 | 98,3% | 0,0% | 20,4% |
| retreinar com gate (A6+GR-5) | 10.709,0 | 609,1 | 10.709,0 | 446 | 98,3% | 0,0% | 20,4% |
| retreinar sem gate | 10.709,0 | 609,1 | 10.709,0 | 446 | 98,3% | 0,0% | 20,4% |

## S3

Ponto de decisão: lote 7 (5 lotes avaliados). Regra da matriz: **P05** — Prior shift relevante, ranking preservado (ações A4, A5, A3).

Gate do challenger (GR-5): **reprovado** — `auc_gain_recent` -0.0023 (limite 0.0) falhou; `auc_loss_reference` 0.0038 (limite 0.01) ok; `calibration_gap_pp` 5.1968 (limite 7.889012637152063) ok; `fairness_gap_increase_pp` 0.1795 (limite 3.0) ok.

| Estratégia | Valor, revisão perdida (US$ mil) | Δ vs. não fazer nada (US$ mil) | Valor, revisão decidida depois (US$ mil) | Valor por proposta (US$) | Aprovação | Revisão | Bad rate dos aprovados |
|---|---|---|---|---|---|---|---|
| não fazer nada | 9.119,7 | 0,0 | 9.119,7 | 304 | 99,8% | 0,0% | 22,7% |
| modo conservador por valor (política) | 11.663,7 | 2.544,1 | 11.262,4 | 389 | 79,7% | 8,8% | 19,7% |
| modo conservador por valor, forçado | 11.663,7 | 2.544,1 | 11.262,4 | 389 | 79,7% | 8,8% | 19,7% |
| regra por valor sem correção, forçada | 9.558,7 | 439,0 | 9.119,7 | 319 | 97,4% | 2,4% | 22,6% |
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
| modo conservador por valor, forçado | 28.032,3 | -6.334,4 | 31.252,6 | 668 | 71,2% | 14,6% | 15,5% |
| regra por valor sem correção, forçada | 28.087,0 | -6.279,8 | 31.313,8 | 669 | 71,3% | 14,6% | 15,5% |
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
  - **Resultado:** o modo conservador por valor rende **+US$ 2,94 mi**, com 14,6% das propostas em revisão (fila limitada a 15% do lote, [ADR-0021](adr/0021-review-queue-capacity.md)). Em 5 seeds novos, a mediana é **+US$ 2,19 mi** (de 2,02 a 2,86): o seed oficial ficou no lado favorável ([ROBUSTNESS.md](ROBUSTNESS.md)).
  - **De onde vem o ganho:** a regra por valor sem correção de risco rende +US$ 0,51 mi. Portanto, cerca de 83% do ganho vem da correção pela razão observado/esperado.
  - **Alternativas de modelo:** recalibrar dá +US$ 0,57 mi. O challenger passa no gate com calibração relativa ([ADR-0020](adr/0020-relative-calibration-gate.md)) e rende +US$ 0,61 mi a partir do lote seguinte.
- **D2, prior shift (S3).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,66 mi** (15,0% em revisão), e a recalibração, sozinha, **+US$ 0,87 mi**. Em 5 seeds novos, as medianas são **+US$ 2,47 mi** (de 2,38 a 2,67) e **+US$ 0,27 mi** (de 0,05 a 0,67): o ganho da recalibração é real, mas o do seed oficial está acima de todos os seeds novos.
  - **Combinação:** a matriz recomenda as duas (A4 automático e A5 humano). O efeito combinado não foi simulado.
- **D6, bug de unidade (S4).**
  - **A política retém o lote e manda corrigir a fonte.**
  - **Custo da quarentena:** depende do que acontece com a fila. Se ela se perde, a quarentena custa US$ 1,72 mi; se é decidida depois do conserto, rende **+US$ 4,01 mi** contra decidir sobre o dado quebrado.
  - **A pior resposta seria o modo conservador:** forçado sobre o bug, perderia US$ 6,3 mi, porque o bug faz o modelo enxergar risco onde não há.

**O teto de 14% foi descartado com evidência** ([ADR-0019](adr/0019-conservative-mode-by-value.md)). Ele recusa empréstimos que continuam lucrativos: −US$ 1,25 mi no S2 e −US$ 2,95 mi no S3. Na carteira já aprovada pelo credor, o corte certo é o de valor esperado negativo, não um teto de bad rate.

**O gate de promoção separa os casos.**
- **Aprovou o challenger do S2** (concept drift), que rende +US$ 0,61 mi.
- **No S1, evitou uma perda de US$ 109 mil.**
- **No S3, deixou US$ 0,26 mi na mesa:** em prior shift, a resposta indicada é recalibrar (+US$ 0,87 mi), não retreinar.
- **No S4, recusou o challenger treinado sobre o bug,** que rende +US$ 1,47 mi só enquanto o bug persiste (ver abaixo).
- **No ponto de decisão quase não há rótulo maduro do regime novo** (atraso de 3 lotes), então retreinar cedo é uma aposta. O gate só aceita quando o challenger supera o champion na ordenação e na calibração.

**Retreinar sobre o bug parece bom, e por isso é perigoso.** Enquanto o bug persiste, o challenger treinado no dado quebrado rende +US$ 1,2 mi, porque aprende a descontar a renda corrompida. É exatamente o modo como o retreino esconde um defeito de dado: quando a fonte for corrigida, esse modelo estará calibrado para um dado que não existe mais. Este cenário não mede esse segundo momento. A regra GR-7 e a precedência do D6 existem para não chegar lá.

**Premissas que limitam a leitura:**
- **Horizonte curto:** de 4 a 7 lotes após o ponto de decisão.
- **Custo da equipe de revisão não modelado.**
- **Revisão em dois extremos:** perdida, ou decidida depois como o champion decidiria.
  - **Sem teto de fila:** decidir depois "como o champion" anulava o ganho, porque o champion aprova de volta toda a faixa de valor negativo.
  - **Com o teto de 15% ([ADR-0021](adr/0021-review-queue-capacity.md)):** o excedente de pior valor esperado é recusado na hora, e o ganho sobrevive mesmo nesse extremo: +US$ 1,07 mi no S2 e +US$ 2,13 mi no S3.
- **Cenários simulados:** os desfechos vêm do oráculo do [ADR-0017](adr/0017-scenario-simulator.md).
