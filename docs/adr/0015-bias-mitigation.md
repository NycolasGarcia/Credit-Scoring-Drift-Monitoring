# ADR-0015 — Mitigação de vieses: limite de gap de aprovação no modo conservador

- **Status:** aceito (limite PROPOSTO em `config/response/policy.yaml`)
- **Data:** 2026-11-17
- **Fase:** F8

## Contexto

O dado não tem gênero nem idade. Os grupos disponíveis são `home_ownership` e as faixas de `emp_length` (as duas são features do modelo) e `addr_state` (fora do modelo de propósito, por ser proxy regional). A análise de vieses ([FAIRNESS.md](../FAIRNESS.md), [RUN-20261117-fairness-ALL-01](../runs/RUN-20261117-fairness-ALL-01.md)) mostrou dois regimes:

- **Regime normal: sem viés relevante na decisão.** O champion aprova 99,8% das propostas, e o gap de aprovação entre grupos fica abaixo de 0,3 p.p. em todos os segmentos. A calibração por grupo fica entre 0,95 e 1,09 (observado/esperado) em `home_ownership` e `emp_length`. Entre estados, a variação é maior (gap de calibração de 0,25 entre os estados com pelo menos 1.000 propostas), com amostras pequenas.
- **Modo conservador: gaps grandes.** Ele corta pelo valor esperado com um fator de risco único, e o corte cai mais sobre quem já tem score mais alto:

  | Cenário | `home_ownership` (RENT × MORTGAGE) | `emp_length` ("desconhecido" × demais) | `addr_state` |
  |---|---|---|---|
  | S2 | gap médio de 13,1 p.p. (máx. 14,5) | 40,8 p.p. (máx. 45,2) | 7,1 p.p. (máx. 9,6) |
  | S3 | 19,3 p.p. (máx. 22,5) | 42,3 p.p. (máx. 45,8) | 8,2 p.p. (máx. 10,7) |

- **Igualdade de oportunidade:** no S2, entre quem pagou, a aprovação é de 89,9% em MORTGAGE contra 79,6% em RENT. No grupo sem tempo de emprego informado (cerca de 4% das propostas, provavelmente renda informal ou autônomos), cai para cerca de 53%, contra 85% a 89% dos demais.
- **Parte do gap é risco real:** quem aluga inadimple 23,0% contra 19,7% de quem tem hipoteca no S2, e o grupo sem tempo de emprego, 28%. Mas o tamanho do corte vai além da diferença de risco.
- **Proxy regional fraco:** a associação de `addr_state` com as features do modelo é fraca (Cramér's V máximo de 0,19, com `home_ownership`).

O §8.4 fixa SEV-2 de fairness em 7 p.p. de aumento do gap. O princípio de não discriminação da LGPD (art. 6º, IX, texto conferido no NV-11) proíbe tratamento para fins discriminatórios ilícitos ou abusivos. O gap não é intencional, mas é um efeito da política que precisa de controle.

## Decisão

1. **Limite de gap no modo conservador.** Com o modo conservador ativo, nenhum grupo de `home_ownership` ou de `emp_length` (faixas de `config/governance/fairness.yaml`) fica mais de **7 p.p.** abaixo do grupo mais aprovado no lote.
2. **Como o limite age.** No grupo cortado demais, voltam a ser aprovadas as propostas retidas pelo modo conservador (motivos R10 e R11) de **maior valor esperado**, só até fechar o gap, com o código de motivo **R12**.
   - Nunca toca o que o próprio champion recusa (R01), nem o kill switch (R20) ou a quarentena (R30).
   - Grupos com menos de 200 propostas no lote ficam fora do cálculo.
3. **`addr_state` fica só monitorado.** Usar a região na decisão reintroduziria o proxy que o modelo exclui por desenho.
4. **Fairness drift monitorado em todo lote.**
   - **Métricas:** `cdm_fairness_gap_pp` e `cdm_fairness_gap_increase_pp`, com o gap da decisão contra o do champion puro no mesmo lote, por segmento.
   - **Alerta:** `CDM_FAIRNESS_GAP`, SEV-1 acima de 3 p.p. de aumento e SEV-2 acima de 7 p.p., com playbook no RUNBOOK.
5. **Mesma regra no job e na comparação de custo.** `src/response/fairness_cap.py` é usado pela etapa `respond` e pelo decisor de `src/response/compare.py`.

## Alternativas consideradas

Valores do modo conservador contra não fazer nada, em US$ mil, no seed oficial ([RUN-20261117-fairness-ALL-01](../runs/RUN-20261117-fairness-ALL-01.md)):

| Alternativa | S2 | S3 | Gaps máximos (casa / emprego / estado) | Por que não |
|---|---|---|---|---|
| Sem limite | 2.942 | 2.662 | S3: 22,5 / 45,8 / 10,7 p.p. | Gaps bem acima do SEV-2 de §8.4 |
| Limite só em `home_ownership` (primeira escolha) | 2.868 | 2.604 | S3: 7,0 / 42,5 / 13,6 p.p. | Deixa o grupo sem tempo de emprego com cerca de 40 p.p. a menos |
| Limite nos três segmentos | 2.738 | 2.477 | S3: 7,0 / 7,0 / 6,5 p.p. | Usa a região na decisão, o que o modelo evita de propósito |
| **Limite em `home_ownership` e `emp_length` (escolhido)** | **2.737** | **2.544** | S3: 7,0 / 6,9 / 11,4 p.p. | — |
| Limite de 3 p.p. (SEV-1) | não registrado em RUN | — | — | Na exploração inicial, só em `home_ownership`, custou de 6% a 9% do ganho. Descartado por custo, sem RUN |
| Remover `home_ownership` e `emp_length` do modelo | — | — | — | O gap vem da regra do modo conservador, não do treino: as features correlatas continuariam carregando o risco. Exigiria retreinar o champion e refazer F2–F7. Não medido |
| Reponderar o treino por grupo | — | — | — | Mesmo motivo: em regime normal não há gap a corrigir. Não medido |

## Consequências

**Boas:**
- **Gaps dentro do limite:** os de `home_ownership` e `emp_length` ficam em até 7 p.p. nos dois cenários. O grupo sem tempo de emprego deixa de ser cortado pela metade.
- **Custo pequeno:** 205 mil (7%) do ganho do modo conservador no S2 e 118 mil (4%) no S3. A política continua rendendo +US$ 2,74 mi e +US$ 2,54 mi contra não fazer nada ([RUN-20261117-response-ALL-02](../runs/RUN-20261117-response-ALL-02.md)).
- **Decisão explicável:** cada proposta devolvida carrega o motivo R12.

**Ruins / custos aceitos:**
- **Tratamento diferenciado por grupo:** os dois atributos já são features do modelo, então o limite não traz informação nova. Mas é uma regra explícita por grupo, e é isso que fica escrito aqui.
- **Gap regional sem limite:** no S3, `addr_state` chega a 11,4 p.p. e dispara o alerta SEV-2 de fairness. Fica com monitoramento e revisão humana.
- **O limite não corrige o risco:** as propostas devolvidas têm valor esperado não positivo com o risco corrigido. É uma escolha de equidade com custo medido, não uma correção de modelo.
- **Números de um seed:** a variação entre seeds está no [estudo de robustez](../ROBUSTNESS.md).

## Como saberemos que a decisão estava errada

- **Custo subestimado:** as propostas aprovadas por R12 inadimplem bem acima do esperado com o risco corrigido, e o custo realizado do limite fica muito acima do medido.
- **Alerta crônico:** o alerta de fairness em `addr_state` fica em SEV-2 de forma persistente, o que pediria rever a exclusão da região do limite.
- **Limite sem efeito:** o gap volta a passar de 7 p.p. com o limite ativo, por exemplo em grupos abaixo de 200 propostas que escapam do cálculo.

## Referências

- `config/response/policy.yaml` (`conservative.fairness`), `config/governance/fairness.yaml`, `src/response/fairness_cap.py`, `src/governance/`
- [FAIRNESS.md](../FAIRNESS.md), [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md), [ADR-0019](0019-conservative-mode-by-value.md), [ADR-0021](0021-review-queue-capacity.md), §8.4, NV-11
