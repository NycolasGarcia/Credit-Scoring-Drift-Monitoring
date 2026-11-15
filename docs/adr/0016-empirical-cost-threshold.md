# ADR-0016 — Premissas de custo empíricas e revisão do limiar de aprovação

- **Status:** aceito em 2026-11-13 (opções B + D, decisão do autor) — supersede o ADR-0007. Uso da opção D (teto de 14%) como corte do modo conservador supersedido pelo [ADR-0019](0019-conservative-mode-by-value.md); o teto segue como métrica de acompanhamento
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

## Alternativas consideradas (opções apresentadas ao autor)

| Opção | Limiar | Aprovação | Prós | Contras |
|---|---|---|---|---|
| A. Premissas empíricas, sem funding | ~0,55 | ~100% | Máximo valor bruto, validado | O modelo deixa de decidir; banda de aprovação (GR-3) e modo conservador perdem sentido; ignora o custo do capital |
| **B. Premissas empíricas + funding declarado (ex.: 5% a.a.)** | ~0,435 | ~99% | Economicamente fundamentado; mantém o limiar como alavanca do modo conservador | A taxa de funding é premissa externa (NV-17); poucas recusas na população filtrada |
| C. Manter 0,33 como apetite de risco declarado | 0,33 | ~94% | Cria uma margem de segurança contra degradação; mais recusas para monitorar | Custa 8,1% do valor realizado no teste; deixa de ser "ótimo" e vira política |
| D. Valor máximo sujeito a teto de bad rate dos aprovados (ex.: ≤ 14%) | depende do teto | — | Explicita o apetite de risco como restrição auditável | Introduz um parâmetro de política a escolher |

## Decisão (aceita: B + D)

**B — regra econômica.** O limiar maximiza o valor esperado com premissas **medidas** no caixa realizado e um **custo de funding declarado de 5% a.a.**, como premissa de política do autor.

O modelo de economia (`src/models/threshold.py`) cobra o funding sobre o saldo-ano que cada desfecho carrega. O saldo-ano do cronograma completo é juros contratuais / taxa. Um bom carrega `margin_realization` desse cronograma, e um mau carrega `bad_interest_realization`.

Premissas em `config/models/cost.yaml` (status ESTIMADO, fonte [RUN-20261113-calib-COST-02](../runs/RUN-20261113-calib-COST-02.md), estimadas no train):

| Premissa | Valor | Origem |
|---|---|---|
| LGD | 0,327 | Medida: perda líquida dos maus, ponderada por valor |
| Realização de juros dos bons | 0,756 | Medida |
| Realização de juros dos maus antes do default | 0,564 | Medida |
| Custo de funding | 5% a.a. | Declarado (política) |

Resultado:

- **Champion v2** ([RUN-20261113-train-REF-02](../runs/RUN-20261113-train-REF-02.md)): mesmo modelo do v1, AUC 0,7001. **Limiar 0,495**. No teste, aprovação de 99,8%, bad rate dos aprovados 15,5% e valor esperado de US$ 942 por proposta. O limiar do F1 (0,195) aprovaria 71,5% com bad rate de 10,5% e US$ 547.
- **Validação final** ([RUN-20261113-calib-COST-03](../runs/RUN-20261113-calib-COST-03.md)), no caixa realizado líquido de funding, no teste: regret de **0,88%** frente ao ótimo realizado (0,435), dentro do sinal de reversão de 2%, e aderência entre curva modelada e realizada de **0,9986**. No limiar adotado: 14 FP (bons recusados, US$ 107 mil de receita perdida), 14 TP (US$ 109 mil de perda evitada) e 2.507 FN (US$ 15,8 mi de perda realizada dos maus aprovados).

**D — apetite de risco como guardrail.** `risk_appetite.max_bad_rate_approved = 0,14` (PROPOSTO) entra em `config/models/cost.yaml` como o teto que o modo conservador (GR-4) vai perseguir na F7. Ao entrar, o modo sobe a régua até o bad rate esperado dos aprovados ficar abaixo do teto. Não altera o limiar base.

**Leitura para o projeto:** em regime normal o modelo aprova quase todos, porque a população já passou pela política do credor de origem. O valor do modelo aparece **sob degradação**: é o ranking que permite ao modo conservador cortar a cauda de risco quando o mundo muda. Esse é o tema das fases F4–F7.

## Consequências

**Boas:**
- O limiar passa a ter base medida e validada contra o caixa real, com regret conhecido.
- A matriz FP/FN fica em dinheiro realizado.

**Ruins / custos aceitos:**
- Qualquer opção depende de uma premissa de política: taxa de funding ou apetite de risco.
- A aprovação próxima de 100% no regime normal é consequência do viés de seleção e precisa ser dita no model card e no vídeo.

## Como saberemos que a decisão estava errada

O regret realizado do limiar adotado passar de 2% em uma janela madura nova (OOT 2014/2015), ou a curva modelada deixar de acompanhar a realizada (Pearson < 0,95).
