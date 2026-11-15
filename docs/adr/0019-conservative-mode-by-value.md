# ADR-0019 — Modo conservador por valor esperado com risco corrigido

- **Status:** aceito (decisão do autor, 2026-11-15) — supersede o item 3 do [ADR-0012](0012-guardrails-conservative-mode.md) e o uso da opção D do [ADR-0016](0016-empirical-cost-threshold.md) no modo conservador
- **Data:** 2026-11-15
- **Fase:** F7

## Contexto

O ADR-0012 definiu o limiar do modo conservador como o maior limiar cujo bad rate esperado dos aprovados coubesse no apetite de 14% (ADR-0016, opção D). A comparação de respostas (caixa 7.9) disparou o sinal de reversão do próprio ADR-0012: nos cenários de degradação, o teto **destruiu valor**.

| Cenário | Teto de 14% (revisão = perda) | Por valor (revisão = perda) |
|---|---|---|
| S2 concept drift | −US$ 1,25 mi | +US$ 2,94 mi |
| S3 prior shift | −US$ 2,95 mi | +US$ 2,66 mi |

Valores contra "não fazer nada", do ponto de decisão ao fim do cenário. RUN e tabela completa em [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md).

O motivo é o mesmo achado da F2: na carteira já aprovada pelo credor de origem, até os empréstimos marginais rendem mais juros do que perdem em inadimplência. O teto recusa empréstimos que continuam lucrativos, enquanto a regra por valor só corta os que deixam de ser.

## Decisão

1. **Com o circuit breaker aberto, cada empréstimo que o champion aprovaria vai para revisão se o seu valor esperado deixa de ser positivo** com o risco corrigido:

   (1 − q)·ganho − q·perda ≤ 0, onde q = min(1, k·p).

   - **p:** score calibrado do champion.
   - **k:** última razão observado/esperado madura, usada só se for maior que 1.
   - **ganho e perda:** os mesmos do ADR-0016.
2. **O teto de 14% sai do corte e vira métrica de acompanhamento:** `cdm_expected_bad_rate_approved`, o bad rate esperado dos aprovados com o risco corrigido. Ele aparece no painel e no resumo de cada lote.
3. **O resto do ADR-0012 continua valendo:** matriz de resposta, breaker com histerese, cadeia de guardrails, códigos de motivo e kill switch. O código R10 passa a significar "valor esperado não positivo com o risco corrigido".
4. **Faixa cinza:** as propostas em revisão nesse modo são, por construção, as de valor esperado negativo. A comparação mostra que o ganho só se realiza se a revisão confirmar a recusa. Se a revisão as aprovasse como o champion, o resultado voltaria a ser o de "não fazer nada". As duas leituras estão na tabela.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Manter o teto de 14% (ADR-0012) | Regra simples, um número de risco declarado | Destrói valor nos cenários de degradação (−US$ 1,25 mi e −US$ 2,95 mi) | Decisão do autor diante da evidência |
| Valor + teto de 14% | Também respeita um limite de risco | Herdaria a perda do teto onde ele morde | O teto não tem base fora da economia neste projeto; fica como métrica |
| Recalibrar automaticamente em vez de modo conservador | Corrige a causa em D2 | Precisa de rótulo maduro e de decisão humana (§8.1, princípio 5); é ação A5 | Complementar, não substituto: o modo conservador protege enquanto a recalibração não sai |

## Consequências

**Boas:**
- **Mesmo critério nas duas pontas:** o modo conservador usa o critério econômico que escolheu o limiar do champion (ADR-0016), agora com o risco corrigido pela evidência de rótulo.
- **Nada muda sem descalibração:** quando o risco está calibrado (k = 1), a regra só corta empréstimos de valor esperado negativo, que o limiar global já tende a recusar.

**Ruins / custos aceitos:**
- **Fila de revisão:** 17% (S2) e 27% (S3) das propostas dos lotes com o breaker aberto. O ganho depende de a revisão confirmar a recusa.
- **Dependência das premissas de custo** (LGD, margem, funding) do ADR-0016: um erro nelas muda o corte.
- **k defasado:** a correção vem de coortes que amadureceram antes; em degradação acelerada, k fica para trás do risco atual.

## Como saberemos que a decisão estava errada

- **Custo:** numa nova rodada da comparação, ou com dado real rotulado, o modo por valor custa mais do que não fazer nada.
- **Revisão:** a revisão aprova a maior parte da faixa cinza; nesse caso, o corte por valor está severo demais ou as premissas de custo estão erradas.
- **Exigência externa de teto de risco** (regulatória ou de capital): ela traria o teto de volta como restrição, com novo ADR.

## Referências

- [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md), `docs/evidence/response/compare.json`
- `src/response/guardrails.py` (`negative_value`, `risk_correction`), `src/response/respond.py`, `config/response/policy.yaml`
