# ADR-0007 — Matriz de custo e limiar de aprovação por valor esperado

> **Nota 2026-11-13 — sinal de reversão disparado.** A análise de sensibilidade (`notebooks/02_modelagem.ipynb`, seção 4; função `cost_sensitivity`) mostrou o limiar ótimo variando entre 0,06 e 0,55 para LGD ∈ [0,4; 0,8] × margem ∈ [0,3; 0,7]. Ele fica dentro de 0,25–0,40 em apenas 6 das 25 combinações. A regra e o limiar vigente (0,33) continuam em uso até que o autor decida a revisão das premissas, registrada em `docs/PROGRESS.md`; a revisão será um ADR novo que supersede este.

- **Status:** aceito (premissas de custo com status PROPOSTO) — **revisão pendente** (ver nota)
- **Data:** 2026-11-12
- **Fase:** F2

## Contexto

Os dois erros de crédito têm custos assimétricos:

- **Aprovar quem inadimple (falso negativo):** perde parte do principal.
- **Recusar bom pagador (falso positivo):** perde a margem de juros que nunca vira receita.

Escolher o limiar por F1 trata os dois erros como equivalentes. O limiar também é o parâmetro que o modo conservador (GR-4, F7) vai deslocar, então precisa de uma base econômica explícita.

## Decisão

**Economia por empréstimo** (`src/models/threshold.py`), calculada só com campos de originação:

- ganho se aprovar um bom pagador = (`installment` × `term` − `loan_amnt`) × **realização de margem**;
- perda se aprovar um mau pagador = `loan_amnt` × **LGD**.

| Premissa | Valor | Status | Racional |
|---|---|---|---|
| LGD | 0,60 | PROPOSTO | Perda após recuperação típica de crédito pessoal sem garantia |
| Realização de margem | 0,50 | PROPOSTO | Juros contratuais líquidos de funding, servicing e pré-pagamento |

As premissas ficam em `config/models/cost.yaml`. O documento declara `status: PROPOSTO`, e um teste garante essa marcação.

**Regra de decisão:** aprovar se score < limiar, com **um limiar global** escolhido na grade 0,02–0,60 (passo 0,005) que maximiza o valor por proposta no conjunto de **calibração**. O limiar é reportado no **teste**.

**Resultado** ([RUN-20261112-train-REF-02](../runs/RUN-20261112-train-REF-02.md), teste da referência):

| Limiar | Aprovação | Bad rate dos aprovados | Valor por proposta (US$) |
|---|---|---|---|
| **0,330 (valor esperado — adotado)** | 94,3% | 14,3% | 445,33 |
| 0,195 (F1 da classe mau) | 71,5% | 10,5% | 411,64 |

No limiar de valor esperado, aprovamos 94,3% com bad rate de 14,3%. O limiar do F1 aprovaria 71,5% com bad rate de 10,5%, rendendo US$ 33,69 a menos por proposta.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Limiar por F1 | Padrão de ML | Ignora a assimetria de custo; recusa 28% e perde valor | Critério errado para crédito |
| Limiar individual por empréstimo (aprovar se p < ganho/(ganho+perda)) | Ótimo teórico por proposta | Taxa de aprovação e banda de saída ficam difíceis de interpretar e monitorar; mais sensível a erro de calibração | Monitoramento precisa de um corte único (GR-3/GR-4) |
| LGD estimada do próprio dado (`recoveries`, `total_pymnt`) | Ancorada no dado | Exige colunas pós-originação fora do loader; análise própria | Pode refinar a premissa depois, sem mudar a regra |

## Consequências

**Boas:**
- O limiar tem justificativa econômica explícita e auditável.
- O valor por proposta fica disponível para comparar respostas à degradação (§7, F7) com a mesma régua.

**Ruins / custos aceitos:**
- O limiar depende das premissas PROPOSTAS. A curva de valor é **achatada** entre 0,25 e 0,40 (notebook `02_modelagem`: US$ 435–465 por proposta no conjunto de calibração), então pequenas mudanças de premissa movem o limiar bastante.
- A aprovação alta (≈ 94%) reflete o **viés de seleção**: o dataset só tem empréstimos já aprovados pela política do credor. Não representa a aprovação sobre a demanda bruta.

## Como saberemos que a decisão estava errada

- A análise de sensibilidade (LGD 0,4–0,8; margem 0,3–0,7) mover o limiar para fora da faixa 0,25–0,40.
- Na F7, a comparação de respostas mostrar que o limiar atual amplifica perdas sob degradação mais do que um limiar mais conservador.

Em qualquer um dos casos: revisar as premissas com o autor e recalibrar o limiar em um novo RUN.
