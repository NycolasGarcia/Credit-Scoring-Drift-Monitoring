# ADR-0021 — Fila de revisão com capacidade e excedente recusado

- **Status:** aceito (capacidade PROPOSTO em `config/response/policy.yaml`); muda o item 4 do [ADR-0012](0012-guardrails-conservative-mode.md), que mandava toda a faixa cinza para revisão
- **Data:** 2026-11-17
- **Fase:** F7

## Contexto

O modo conservador por valor ([ADR-0019](0019-conservative-mode-by-value.md)) manda para revisão humana o que o champion aprovaria, mas cujo valor esperado não fica positivo com o risco corrigido. Nenhum documento dizia quanto essa fila pode receber.

- **O game day mostrou o problema.** No [INC-0001](../incidents/0001-s2-concept-drift-dti.md), de 14% a 21% de cada lote (855 a 1.233 de 6.000 propostas) foram para revisão. Na comparação de respostas, a fila chegava a 26,6% no S3 ([RUN-20261115-response-ALL-02](../runs/RUN-20261115-response-ALL-02.md)).
- **O ganho dependia do revisor.** Na mesma comparação, se a fila fosse decidida depois "como o champion decidiria", o valor do modo conservador voltava exatamente ao de não fazer nada. Todo o ganho vinha de a revisão confirmar a recusa.
- **O ADR-0012 já previa esta saída.** Seu sinal de reversão: "o volume da fila de revisão inviabiliza a operação. Nesse caso, rever o apetite ou recusar automaticamente parte da faixa cinza, com novo ADR".

## Decisão

1. **Capacidade por lote.** A fila de revisão do modo conservador recebe no máximo `review_capacity` do lote: 15% (PROPOSTO, premissa de capacidade operacional, sem dado de equipe real).
2. **Quem fica na fila.** Entre os candidatos à revisão, ficam os de maior valor esperado, ou seja, os mais próximos de zero: são os casos em que um revisor tem chance de achar informação que salve a proposta. Os de pior valor esperado são **recusados**, com o código de motivo próprio **R11**.
3. **Onde vale.** O teto vale só para a faixa do modo conservador (R10). O kill switch (R20) e a quarentena preventiva (R30) continuam retendo o lote inteiro: são exceções que escalam para decisão humana (A9, A2), não operação de rotina.
4. **Mesma regra na comparação de custo.** A cadeia do job (`src/response/guardrails.py`) e o decisor da comparação (`src/response/compare.py`) usam a mesma função (`review_overflow`).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Sem teto (decisão anterior) | Toda decisão negativa passa por humano | Fila de 15% a 27% do lote; o ganho some se a revisão aprovar de volta | Medido no game day e na comparação |
| Recusar toda a faixa, sem revisão | Sem fila | Nenhuma revisão humana para quem o modelo degradado recusou | Conflita com a revisão de decisão automatizada (hipótese do art. 20 da LGPD, NV-11) |
| Excedente aprovado pelo champion | Não recusa ninguém a mais | Devolve justamente os casos de pior valor esperado | Desfaz o modo conservador |
| Teto em número absoluto de propostas | Reflete o tamanho fixo de uma equipe | Depende do tamanho do lote; os cenários usam lote fixo e não ganham nada com isso | Fica como variação quando houver dado de equipe |
| Priorizar a fila por score em vez de valor | Mais simples | O critério do modo conservador é o valor; o score ignora o tamanho e a taxa do empréstimo | Coerência com o ADR-0019 |

## Consequências

Números de [RUN-20261117-response-ALL-01](../runs/RUN-20261117-response-ALL-01.md), comparados com o RUN anterior:

**Boas:**
- **O valor com a revisão perdida não muda:** no lote, revisão e recusa valem 0. O modo conservador continua rendendo +US$ 2,94 mi no S2 e +US$ 2,66 mi no S3.
- **A fila fica dentro do teto:** 14,6% no S2 e 15,0% no S3 (antes, 17,4% e 26,6%).
- **O ganho não depende mais do revisor.** Com a fila decidida depois como o champion decidiria, o modo conservador rende +US$ 1,07 mi no S2 e +US$ 2,13 mi no S3; antes, rendia zero.

**Ruins / custos aceitos:**
- **Recusa automática de parte da faixa.** Isso é uma decisão automatizada sobre um modelo sabidamente degradado. A mitigação é o código de motivo R11, que permite ao titular pedir revisão depois. O enquadramento legal é hipótese até fechar o NV-11 (F8).
- **15% é premissa, não medida.** Sem dado de equipe nem de custo de revisão, o número é trocável sem cerimônia.
- **Pior se o modo conservador for forçado sobre dado quebrado.** No S4, forçado, o valor com a revisão decidida depois cai de US$ 34,37 mi para US$ 31,25 mi, porque o excedente recusado era de bons pagadores com a renda corrompida. A política não força o modo conservador no D6 (regra P02), e o resultado reforça essa precedência.

## Como saberemos que a decisão estava errada

- **Revisão revertendo R11:** a revisão humana, quando consultada, aprovaria boa parte das propostas recusadas por R11. Nesse caso, o critério de prioridade (valor esperado) não separa bem quem merece revisão.
- **Fila ociosa:** a fila fica sistematicamente abaixo do teto enquanto o modo conservador está ativo, e o teto não está fazendo nada.
- **Contestação:** titulares contestam recusas R11 em volume. Nesse caso, rever junto com a análise de governança da F8.

## Referências

- `config/response/policy.yaml` (`conservative.review_capacity`), `src/response/guardrails.py` (`review_overflow`, R11), `src/response/compare.py`
- [INC-0001](../incidents/0001-s2-concept-drift-dti.md) (item de ação 4), [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md), [ADR-0012](0012-guardrails-conservative-mode.md), [ADR-0019](0019-conservative-mode-by-value.md)
