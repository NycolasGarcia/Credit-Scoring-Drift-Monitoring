# ADR-0012 — Guardrails e modo conservador

- **Status:** aceito; **item 3 (limiar pelo teto de 14%) supersedido pelo [ADR-0019](0019-conservative-mode-by-value.md)** em 2026-11-15, depois que a comparação de custo disparou o sinal de reversão deste ADR
- **Data:** 2026-11-15
- **Fase:** F7

## Contexto

O detector diagnostica o tipo de degradação, mas o rótulo chega meses depois (§8.1, princípio 2). No dado real, o drift de entrada aparece em 2014 e a confirmação com rótulo só em 2017 ([DRIFT_EVALUATION.md](../DRIFT_EVALUATION.md)). Enquanto o diagnóstico não fecha, alguma coisa precisa proteger a decisão de crédito, e essa coisa só pode fazer o que é reversível (§8.1, princípio 5).

Insumos já decididos:
- **Apetite de risco:** teto de bad rate entre aprovados de 14% (PROPOSTO, [ADR-0016](0016-empirical-cost-threshold.md), opção D), reservado ao modo conservador.
- **Gatilho:** os alertas SEV-2 de L3 e L4, com o corte do bad rate validado no [ADR-0018](0018-l4-sev2-cut.md).

## Decisão

1. **Matriz de resposta declarativa** (`config/response/policy.yaml`).
   - **Regras:** diagnóstico, nível máximo dos alertas de saída e de desempenho (L3/L4) e nível do lote levam a uma lista de ações do catálogo §8.5, cada uma marcada como automática ou humana. Vale a primeira regra que casa.
   - **Única fonte do modo conservador:** é a matriz, e não um gatilho separado, que pede o modo conservador (A4).
   - **Drift só de entrada (L2) não muda a política de crédito,** como manda a árvore §8.7.
2. **Circuit breaker (GR-4).** Abre quando uma regra pede A4 e fecha depois de 2 lotes seguidos sem novo pedido (histerese, PROPOSTO), para não alternar a política a cada lote. O override humano (`conservative_mode: on|off`) tem precedência.
3. **Limiar de política.** É o maior limiar cujo bad rate esperado entre os aprovados cabe no apetite de 14%.
   - **Correção pelo rótulo:** quando já há rótulo maduro, o risco do modelo é multiplicado pela última razão observado/esperado, mas só se ela for maior que 1. Assim, o limiar aperta na medida da subestimação medida.
   - **Sem rótulo:** sem nenhum rótulo maduro, vale o score calibrado.
4. **Faixa cinza → revisão humana.** Com o breaker aberto, os casos que o champion aprovaria e o limiar de política não aprova vão para revisão, não para recusa automática. A intenção é preservar a possibilidade de revisão de decisão automatizada (art. 20 da LGPD; hipótese até fechar o NV-11 na F8).
5. **Cadeia de guardrails por decisão (Chain of Responsibility).** Cada etapa decide as linhas que lhe cabem e passa o resto adiante:

   | Ordem | Etapa | Efeito | Código |
   |---|---|---|---|
   | 1 | kill switch (GR-9) | tudo vai para revisão | R20 |
   | 2 | quarentena preventiva (A2, suspeita de bug D6) | lote inteiro retido para revisão | R30 |
   | 3 | modo conservador (GR-4) | faixa cinza vai para revisão | R10 |
   | 4 | limiar do champion | aprovação ou recusa | R00 / R01 |

   Toda decisão sai com o seu código de motivo.
6. **Sem deploy para mudar a política.** O arquivo de política é relido a cada lote: mudar o kill switch ou o override vale a partir do lote seguinte. O modo `dry_run` registra as ações sem alterar decisões, útil para ensaiar uma política nova.
7. **Fora da automação:** recalibrar (A5), promover (A7), fazer rollback (A8) e suspender (A9) ficam como ações humanas. O job as registra, mas não as executa.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Limiar conservador fixo (ex.: 0,33 do v1) | Simples | Não reage ao tamanho da degradação; sem ligação com um apetite de risco declarado | O limiar derivado do apetite tem justificativa auditável |
| Recusar automaticamente a faixa cinza | Sem fila manual | Recusa por modelo sabidamente degradado, sem revisão humana | Conflita com a revisão de decisão automatizada (hipótese do art. 20) |
| Abrir o breaker com SEV-1 | Reage mais cedo | SEV-1 é atenção; o falso alarme de SEV-2 é 0% no controle, o de SEV-1 não | Fadiga e custo de política sem confirmação |
| Abrir com drift de entrada (L2) | Mais antecipado | Drift não é degradação: no S1, a decisão continua certa (D1) | Contra §8.1, princípio 1 |
| Breaker sem histerese | Mais simples | A política oscila lote a lote quando o sinal fica na fronteira | Instabilidade de decisão para o cliente |
| Retreinar automaticamente na degradação | Resposta "completa" | Irreversível sem gate; pode aprender ruído ou bug | Contra §8.1, princípios 5 e 7 (ADR-0013) |

## Consequências

**Boas:**
- **Decisão protegida antes do rótulo:** no S2, o modo conservador abre no lote 8, o primeiro em SEV-2.
- **Decisões explicáveis:** cada uma tem código de motivo.
- **Política mutável sem deploy:** muda pelo YAML e é testável (`tests/test_response.py`).

**Ruins / custos aceitos:**
- **Fila de revisão grande:** no S2, 24% a 31% de cada lote vai para revisão, porque o teto de 14% corrigido pela razão de ~1,3 exige um corte forte. Se essa fila é operável e compensa é uma questão de custo, medida na comparação de respostas (caixa 7.9).
- **D6 retém o lote inteiro:** decisões atrasadas até a fonte ser corrigida.
- **Revisão sem valor no lote:** a comparação de custo trata proposta em revisão como não aprovada no lote (`manual_review_value: 0`). O custo da equipe de revisão não está modelado.

## Como saberemos que a decisão estava errada

- **Custo:** a comparação de respostas mostra que o modo conservador custa mais (receita recusada) do que não fazer nada nos cenários de degradação.
- **Falso alarme:** o breaker abre no controle (S0).
- **Fila inviável:** o volume da fila de revisão inviabiliza a operação. Nesse caso, rever o apetite ou recusar automaticamente parte da faixa cinza, com novo ADR.

## Referências

- `config/response/policy.yaml`, `src/response/` (settings, policy, guardrails, respond)
- §8.5, §8.6 (GR-3, GR-4, GR-9), [ADR-0016](0016-empirical-cost-threshold.md), [ADR-0018](0018-l4-sev2-cut.md), NV-11
