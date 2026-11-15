# Avaliação do detector de drift

> Gerado por `make drift-docs` (`src/monitoring/docs.py`). Não editar à mão.

Cada cenário tem ground truth conhecido ([SCENARIOS.md](SCENARIOS.md)); o detector é avaliado como um classificador (§8.8). Atraso em lotes após o início do drift; falso alarme medido nos lotes sem drift (S0 inteiro, ou antes do início).

## Resumo por cenário

| Cenário | RUN | Diagnóstico certo | 1º SEV-1 (atraso) | 1º SEV-2 (atraso) | Camadas esperadas | Camadas acionadas | Atribuição recall / precisão | Acurácia do diagnóstico | Falso alarme |
|---|---|---|---|---|---|---|---|---|---|
| S0 | [RUN-20261115-monitor-S0-01](runs/RUN-20261115-monitor-S0-01.md) | none | — (—) | — (—) | — | — | — / — | — | 0.0% |
| S1 | [RUN-20261115-monitor-S1-01](runs/RUN-20261115-monitor-S1-01.md) | D1 | 5 (2) | 7 (4) | L2/L3 | L2/L3 | 100.0% / 100.0% | 100.0% | 0.0% |
| S2 | [RUN-20261115-monitor-S2-01](runs/RUN-20261115-monitor-S2-01.md) | D3 | 8 (5) | 8 (5) | L4 | L4 | — / — | 100.0% | 0.0% |
| S3 | [RUN-20261115-monitor-S3-01](runs/RUN-20261115-monitor-S3-01.md) | D2 | 7 (3) | 7 (3) | L4 | L4 | — / — | 100.0% | 0.0% |
| S4 | [RUN-20261115-monitor-S4-01](runs/RUN-20261115-monitor-S4-01.md) | D6 | 5 (0) | 5 (0) | L2/L3 | L2/L3/L4 | 100.0% / 100.0% | 100.0% | 0.0% |
| S5 | [RUN-20261115-monitor-S5-01](runs/RUN-20261115-monitor-S5-01.md) | unknown | 1 (—) | 11 (—) | L2/L3/L4 | L2/L4 | — / — | — | — |

## Relatórios Evidently

Janela escolhida pelo detector (do 1º alerta em diante; últimos lotes se nada alertou). Teste por coluna: `psi_ref` (PSI com bins da referência, registrado no Evidently), limiar 0.1. Última coluna: diferença máxima para o PSI próprio nas colunas sem nulos.

| Cenário | HTML | Linhas | Colunas acima do limiar | Máx. dif. (sem nulos) |
|---|---|---|---|---|
| S0 | [S0_evidently.html](evidence/drift/S0_evidently.html) | 35993 | — | 0.000000 |
| S1 | [S1_evidently.html](evidence/drift/S1_evidently.html) | 42000 | int_rate, dti, score, annual_inc | 0.000000 |
| S2 | [S2_evidently.html](evidence/drift/S2_evidently.html) | 23989 | — | 0.000000 |
| S3 | [S3_evidently.html](evidence/drift/S3_evidently.html) | 29989 | — | 0.000000 |
| S4 | [S4_evidently.html](evidence/drift/S4_evidently.html) | 41989 | annual_inc, score | 0.000000 |
| S5 | [S5_evidently.html](evidence/drift/S5_evidently.html) | 50000 | verification_status, int_rate, revol_util, percent_bc_gt_75, bc_util | 0.000000 |

## p-valor versus tamanho de efeito (NV-10)

| Cenário | Pares lote-feature | KS p < 0,05 | PSI ≥ SEV-1 | KS rejeita com PSI abaixo de SEV-1 |
|---|---|---|---|---|
| S0 | 348 | 3.4% | 0.0% | 3.4% |
| S1 | 348 | 12.1% | 4.9% | 7.2% |
| S2 | 348 | 2.3% | 0.0% | 2.3% |
| S3 | 348 | 3.4% | 0.0% | 3.4% |
| S4 | 348 | 2.6% | 2.0% | 0.6% |
| S5 | 1740 | 98.3% | 11.5% | 86.8% |

## Leitura

Números por lote em `docs/evidence/drift/<cenário>.json`; RUNs na tabela acima.

**Os diagnósticos saíram certos em todos os cenários com ground truth.** Todo lote que alertou após o início do drift recebeu o diagnóstico esperado: D1 no S1, D3 no S2, D2 no S3 e D6 no S4. No controle (S0), nenhum dos 12 lotes alertou; no bootstrap, o falso alarme foi de 0,2% em SEV-1 e 0% em SEV-2 ([THRESHOLDS.md](THRESHOLDS.md)).

**S1 — choque econômico.**
- **Detecção:** L2 dispara no lote 5, com metade da intensidade; `int_rate` acusa primeiro. SEV-2 vem no lote 7, quando o PSI do score passa de 0,10 (0,131).
- **Diagnóstico:** a L4 fica quieta, porque o modelo continua calibrado, e o diagnóstico é D1 em 7 de 7 lotes. Drift sem degradação: o caso em que retreinar seria um erro.
- **Atribuição:** as 3 features injetadas (100%), sem falso positivo. A parcela (`installment`), recalculada pela amortização, é um efeito mecânico (`secondary_features` no manifesto): muda pouco com +3 p.p. de juros e fica com PSI 0,009, longe do corte.

**S2 — concept drift.**
- **Detecção:** entradas e score nunca alertam. A L4 acusa no lote 8, um atraso de 5 lotes: 3 de rótulo e 2 de rampa até o efeito ficar visível.
- **Diagnóstico:** D3 em 5 de 5 lotes. O descolamento observado/esperado se concentra em `dti` (amplitude de 0,81 a 1,04 em logit, contra o corte de 0,5), que é exatamente o segmento injetado. O detector aponta onde está o problema sem ver o manifesto.

**S3 — prior shift.**
- **Detecção:** a L4 acusa no lote 7, ou seja, o início (lote 4) mais o atraso de rótulo (3), o mínimo possível.
- **Diagnóstico:** D2 em 5 de 5 lotes, com descolamento uniforme (amplitude ≤ 0,31).

**S4 — bug de unidade.**
- **Detecção:** no próprio lote do início (atraso 0), já em SEV-2, com a assinatura ÷12 confirmada em 7 de 7 lotes e atribuição perfeita (`annual_inc`).
- **Dano real também em L4:** a partir do lote 8, a queda de AUC fica entre 0,03 e 0,05. O bug estraga a ordenação de verdade.
- **Diagnóstico:** continua D6, porque D6 vem antes na árvore. A resposta certa é corrigir a fonte, nunca retreinar sobre o dado quebrado.

**S5 — produção natural (2014–2018).**
- **Entradas:** L2 dispara desde 2014-02, com `verification_status` (mudança de mix de verificação de renda). `int_rate` entra em 2014-09, e o SEV-2 começa em 2014-12.
- **Saída:** a L3 nunca dispara. O PSI do score fica no máximo em 0,078 e a aprovação varia no máximo 1,3 p.p.: a distribuição do score é estável em cinco anos, mesmo com as entradas mudando.
- **Desempenho:** a L4 só existe a partir de 2017-01, quando vencem os primeiros contratos de 36 meses. Ali, observado/esperado sobe de 1,03 (coorte 2014-01) para 1,39 (coorte 2015-12), com AUC entre 0,67 e 0,71: o modelo subestima o risco sem perder a ordenação. O diagnóstico passa a D2 a partir de 2017-09, o caso de recalibração (F7).

## Lições

1. **O sinal antecipado chega três anos antes da confirmação.** No dado real, o drift de entrada aparece em 2014; a confirmação com rótulo maduro, só em 2017–2018. Esperar a L4 para agir significa três anos de decisões com risco subestimado. É o argumento central para guardrails que agem sobre L2/L3 (F7).
2. **O corte de SEV-2 de planejamento escondia a degradação com rótulo.**
   - **Problema:** com o SEV-2 da razão observado/esperado em 1,5, S2 e S3 degradavam de fato (bad rate +5 a +7 p.p.) e ficavam em SEV-1, porque as razões máximas eram 1,37 e 1,499. O modo conservador (GR-4), que reage a SEV-2, não dispararia.
   - **Correção:** o corte foi refeito por uma regra declarada antes da execução, usando só a distribuição nula ([ADR-0018](adr/0018-l4-sev2-cut.md), [RUN-20261115-calib-L4CUT-01](runs/RUN-20261115-calib-L4CUT-01.md)): 1,25.
   - **Validação:** nas variantes de S2 e S3 com seeds novas, as intensidades oficiais passam de 0/3 para 3/3 detectadas em SEV-2.
   - **Resultado:** S2 e S3 chegam a SEV-2 já no primeiro alerta (lotes 8 e 7).
3. **O p-valor não serve como gatilho (NV-10).** No S5, o KS rejeita em 98,3% dos pares lote–feature, enquanto o PSI passa do corte em 11,5%. No controle, rejeita em 3,4%, perto dos 5% nominais.
4. **O Evidently concorda com o detector.** O `psi_ref` dentro do Evidently reproduz o PSI próprio sem diferença (0,000000) em todas as colunas sem nulos, nos seis relatórios.
5. **Errata da F2.** O PSI do score de 0,226 registrado para o OOT 2015 ([ADR-0006](adr/0006-base-model.md), model card) é um artefato do filtro de maturação. No snapshot, os maduros de 2015 são 100% de 36 meses; os de 60 meses, mais arriscados, ficam de fora. Sobre todas as propostas de 2015, o PSI do score é 0,009. A estabilidade de score aqui medida no S5 é o número correto.
