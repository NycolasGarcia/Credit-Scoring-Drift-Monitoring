# ADR-0016 — Premissas de custo empíricas e revisão do limiar de aprovação

- **Status:** proposto (aguarda decisão do autor; quando aceito, supersede o ADR-0007)
- **Data:** 2026-11-13
- **Fase:** pós-F2 (antes de F7)

## Contexto

O ADR-0007 escolheu o limiar 0,33 por valor esperado com premissas **propostas** (LGD 0,60; realização de margem 0,50). A análise de sensibilidade disparou o sinal de reversão do próprio ADR: o limiar ótimo varia de 0,06 a 0,55 na grade plausível. Por isso as premissas foram **medidas no caixa realizado** do credor e o limiar foi **validado contra o caixa real** em dado não usado na escolha.

Método (`make cost`, `src/models/economics.py` e `src/models/cost_calibration.py`):

1. Colunas de pagamento (`use: custo` no inventário) lidas só em agregado. Caixa líquido = `total_pymnt` − `funded_amnt` − `collection_recovery_fee`; a identidade `total_pymnt` = principal + juros + multas + recuperações foi verificada no dado bruto.
2. Premissas estimadas no **train**, ponderadas por valor.
3. Limiar escolhido na **calibração**.
4. Validação no **teste** (referência 2013, nunca usada nas etapas anteriores) contra o valor que cada decisão de fato rendeu.

Resultados ([RUN-20261113-calib-COST-01](../runs/RUN-20261113-calib-COST-01.md), evidência em `docs/evidence/models/cost_validation.json`):

| | Premissas propostas (ADR-0007) | Premissas empíricas |
|---|---|---|
| LGD | 0,60 | **0,327** (mediana por empréstimo 0,355; p25–p75 0,11–0,58) |
| Realização de juros | 0,50 | **0,756** (mediana 0,926) |
| Limiar escolhido (calibração) | 0,330 | 0,550 |
| Valor realizado no teste no limiar escolhido (US$/proposta) | 1.887 | 2.052 |
| Ótimo realizado no teste | 0,555 → US$ 2.054 | 0,555 → US$ 2.054 |
| **Regret** (perda vs. ótimo realizado) | **8,1%** | **0,05%** |
| Aderência curva modelada × realizada (Pearson) | 0,921 | **0,999** |

Matriz FP/FN no teste, no limiar 0,33 com caixa realizado:

- **FN** (mau aprovado): 2.178 casos, perda realizada de US$ 10,9 mi (média US$ 5.021).
- **FP** (bom recusado): 577 casos, receita perdida de US$ 5,0 mi (média US$ 8.671).
- **TP** (mau recusado): 343 casos, perda evitada de US$ 2,3 mi.

Recusar um mau evita, em média, menos do que recusar um bom custa. Por isso o ótimo empurra para aprovar mais.

**Sensibilidade ao custo de funding** (caixa realizado, teste). O custo de funding = taxa × saldo-ano, com saldo-ano = `total_rec_int` / `int_rate`, sem supor prazo:

| Funding a.a. | Limiar ótimo | Aprovação | US$/proposta (ótimo) | US$/proposta (aprovar todos) |
|---|---|---|---|---|
| 0% | 0,555 | 99,97% | 2.054 | 2.053 |
| 3% | 0,435 | 99,1% | 1.375 | 1.373 |
| 5% | 0,435 | 99,1% | 927 | 919 |
| 8% | 0,400 | 98,2% | 257 | 238 |
| 10% | 0,020 | 0,4% | −2 | −216 |

**Leitura:** nesta população, que **já foi aprovada pela política do credor de origem** (viés de seleção), o valor econômico de recusar é pequeno enquanto o custo de funding fica abaixo de ~8% a.a. A 10%, a carteira inteira dá prejuízo. O modelo de custo em si está validado: com premissas empíricas, ele reproduz o caixa real.

## Opções para decisão

| Opção | Limiar | Aprovação | Prós | Contras |
|---|---|---|---|---|
| A. Premissas empíricas, sem funding | ~0,55 | ~100% | Máximo valor bruto, validado | O modelo deixa de decidir; banda de aprovação (GR-3) e modo conservador perdem sentido; ignora o custo do capital |
| **B. Premissas empíricas + funding declarado (ex.: 5% a.a.)** | ~0,435 | ~99% | Economicamente fundamentado; mantém o limiar como alavanca do modo conservador | A taxa de funding é premissa externa (NV-17); poucas recusas na população filtrada |
| C. Manter 0,33 como apetite de risco declarado | 0,33 | ~94% | Cria uma margem de segurança contra degradação; mais recusas para monitorar | Custa 8,1% do valor realizado no teste; deixa de ser "ótimo" e vira política |
| D. Valor máximo sujeito a teto de bad rate dos aprovados (ex.: ≤ 14%) | depende do teto | — | Explicita o apetite de risco como restrição auditável | Introduz um parâmetro de política a escolher |

## Recomendação

**B como regra econômica, combinada com D como guardrail.** O limiar econômico usa premissas empíricas mais um custo de funding declarado. O apetite de risco, um teto de bad rate dos aprovados, vira o limite do modo conservador (GR-4) na F7, em vez de ser embutido no limiar base.

Implementar B exige estender `loan_economics` com o termo de funding: saldo-ano esperado = juros esperados / taxa. Depois, novo `make train` para registrar o champion v2 com o limiar revisado e um novo `make cost` para validar.

## Consequências

**Boas:**
- O limiar passa a ter base medida e validada contra o caixa real, com regret conhecido.
- A matriz FP/FN fica em dinheiro realizado.

**Ruins / custos aceitos:**
- Qualquer opção depende de uma premissa de política: taxa de funding ou apetite de risco.
- A aprovação próxima de 100% no regime normal é consequência do viés de seleção e precisa ser dita no model card e no vídeo.

## Como saberemos que a decisão estava errada

O regret realizado do limiar adotado passar de 2% em uma janela madura nova (OOT 2014/2015), ou a curva modelada deixar de acompanhar a realizada (Pearson < 0,95).
