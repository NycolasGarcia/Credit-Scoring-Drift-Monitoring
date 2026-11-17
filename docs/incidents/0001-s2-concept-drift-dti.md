# INC-0001 — Bad rate acima do esperado no segmento de DTI alto (game day S2)

- **Status:** fechado (postmortem concluído; itens 1, 2 e 4 resolvidos na F7, item 5 na F8, item 3 em aberto)
- **Severidade:** SEV-2
- **Cenário / RUN:** S2 · [RUN-20261117-gameday-S2-01](../runs/RUN-20261117-gameday-S2-01.md)
- **Simulado:** sim (game day, §11.7)

## Resumo

No lote 8 (set/2014), o alerta `CDM_BAD_RATE_RATIO` disparou em SEV-2: nos rótulos que amadureceram, a inadimplência observada ficou 1,27× acima da esperada pelo modelo, concentrada em quem tem DTI alto.

- **Ação automática:** o modo conservador entrou no mesmo lote e mandou para revisão de 855 a 1.233 propostas por lote.
- **Ação humana:** treinar o challenger em sombra. Ele passou no gate de promoção já no lote seguinte.
- **Ground truth:** o diagnóstico (D3 no segmento de DTI alto) bateu com o manifesto.
- **Maior achado:** a árvore de decisão §8.7 apontaria a resposta errada para este tipo de concept drift.

## Linha do tempo

Horários do dia 2026-11-17. Lote = mês de safra simulado.

| Momento | Hora | Lote | Evento |
|---|---|---|---|
| Início da degradação (injetada) | — | 3 | Desconhecido do operador até a comparação final (manifesto aberto às 09:55) |
| Primeiro sinal possível | — | 6 | Primeira coorte afetada amadurece (atraso de rótulo de 3 lotes). Razão observado/esperado de 1,06, abaixo do SEV-1 (1,2): sem alerta |
| Sinal abaixo do corte | — | 7 | Razão de 1,19, ainda abaixo do SEV-1: sem alerta |
| Alerta disparado | 09:53 | 8 | `CDM_BAD_RATE_RATIO` SEV-2. Razão de 1,27, diagnóstico D3, segmento `dti` (gap de 0,81). Regra P03 da matriz. INC-0001 aberto |
| Ação automática | 09:53 | 8 | A4 modo conservador (GR-4): 855 propostas para revisão, correção de risco k = 1,27 |
| Triagem | 09:53 | 8 | Árvore §8.7 e playbook `CDM_BAD_RATE_RATIO` (detalhe em Diagnóstico) |
| Ação humana | 09:53 | 8 | A6: challenger treinado com 17.990 linhas maduras e aprovadas no contrato (GR-7, GR-8) |
| Verificação | 09:54 | 9 | Modo conservador segue ativo (k = 1,36; 1.224 em revisão). Na sombra, challenger com AUC de 0,728 contra 0,723 do champion e razão de 1,13 contra 1,36. Gate GR-5 aprovado |
| Comparação com o ground truth | 09:55 | — | Manifesto do S2 aberto (detalhe em Causa raiz) |

## Detecção

- **Camada:** L4 (desempenho com rótulo maduro). L0 a L3 ficaram quietos o tempo todo: contrato `partial` (menos de 1% das linhas em quarentena, igual ao controle), nenhuma etapa com falha, PSI do score ≤ 0,003, nenhum alerta de feature.
- **Alerta:** `CDM_BAD_RATE_RATIO`, SEV-2 do lote 8 ao 11 (razão entre 1,27 e 1,37).
- **Atraso de detecção:**
  - 5 lotes desde o início da degradação;
  - 2 lotes desde o primeiro sinal possível, já que o atraso de rótulo impede qualquer sinal em L4 antes do lote 6.

## Diagnóstico

- **Código da taxonomia:** D3 (concept drift), concentrado no segmento de DTI alto.
- **Raciocínio na árvore §8.7, seguida como está escrita:**
  1. L0/L1 falharam? Não: contrato no padrão do controle e nenhuma etapa com falha.
  2. Mudança abrupta, num lote só, com fator constante? Não: sem `CDM_UNIT_BUG_SUSPECTED`, e a razão subiu aos poucos (1,06 → 1,19 → 1,27).
  3. Drift em L2 sem L3? Não há drift em L2.
  4. Drift em L3 com rótulo imaturo? Não há drift em L3.
  5. L4 disponível. A AUC está estável (0,71–0,72, sem queda) e o bad rate está acima do esperado. **Pela árvore, isso é D2 → recalibrar.**
- **Divergência com o playbook:** o playbook do alerta (`CDM_BAD_RATE_RATIO` no [RUNBOOK](../RUNBOOK.md)) distingue D2 (descolamento uniforme) de D3 (descolamento concentrado num segmento). O detector classificou D3 pelo gap no segmento `dti`, e o playbook manda challenger em sombra e gate (A6, GR-5).
- **Decisão do operador:** seguir o playbook do alerta, que é mais específico, e registrar a divergência como achado.

## Causa raiz

Segundo o manifesto ([evidence/scenarios/S2.json](../evidence/scenarios/S2.json), RUN-20261113-sim-S2-01):
- **O que mudou:** quem tem DTI no topo da distribuição (≥ p70 da referência) passou a inadimplir mais, com logit +1,0. A mudança é gradual a partir do lote 3 e fica completa no lote 6.
- **O que não mudou:** as entradas e o score. Por isso só L4 podia ver o problema.

O diagnóstico do operador (D3, segmento `dti`, sem drift de entrada) **bateu com o ground truth** em tipo, feature e camada. A narrativa econômica (desemprego atinge primeiro quem já está endividado) e o grafo causal estão na [análise causal](../CAUSAL_ANALYSIS.md#6-causa-raiz-do-inc-0001).

## Ação tomada

- **Códigos:** A4 (automática), A3 e A6 (humanas) e A7 (recomendada).
- **A7:** o gate aprovou o challenger no lote 9, mas ele **não foi promovido sobre o champion real**, porque o cenário é simulado. Promoção e rollback foram exercidos no registry de ensaio ([RUN-20261115-response-DRILL-01](../runs/RUN-20261115-response-DRILL-01.md)).
- **Guardrails acionados:** GR-4 (circuit breaker → modo conservador por valor), GR-7 e GR-8 (travas de treino do challenger) e GR-5 (gate).

## Impacto estimado

Fonte: [RUN-20261115-response-ALL-02](../runs/RUN-20261115-response-ALL-02.md), cenário S2, do lote 8 ao 11, em US$ mil. O ponto de decisão do RUN coincide com o lote do alerta.

| Resposta | Valor | Δ vs. não fazer nada | Bad rate dos aprovados |
|---|---|---|---|
| Não fazer nada | 10.099,9 | — | 21,0% |
| Modo conservador por valor (o que rodou) | 13.042,2 | +2.942,3 | 18,0% (17,4% em revisão) |
| Retreinar com gate (A6 + GR-5) | 10.709,0 | +609,1 | 20,4% |
| Recalibrar (A5, o que a árvore §8.7 indicaria) | 10.670,6 | +570,6 | 20,4% |

- **Origem do ganho do modo conservador:** ele vem de **não aprovar** a faixa mandada para revisão. Se a fila fosse decidida depois pelo próprio champion, o valor voltaria ao de não fazer nada. A revisão manual só preserva o ganho se o revisor recusar a maior parte da faixa.
- **Lotes 3 a 7 (drift sem alerta):** o custo não foi medido. O RUN de comparação começa no ponto de decisão.

## O que funcionou

- **Separação D1 × D3 (§8.8):** contrato, drift de entrada e score ficaram quietos, e só L4 alarmou. Nenhum falso positivo em L2 ou L3.
- **Atribuição:** o detector apontou o segmento certo (`dti`) entre as features do top-k.
- **Modo conservador:** entrou automaticamente no mesmo lote do alerta, e a correção de risco acompanhou a razão observada lote a lote.
- **Challenger:** as travas GR-7 e GR-8 deixaram treinar com volume suficiente (17.990 linhas), e o gate aprovou o challenger no primeiro lote de rótulos novos.
- **Determinismo:** a triagem parada no lote 8 e o RUN completo produziram números idênticos.

## O que falhou

1. **A árvore §8.7 levaria à resposta errada.** Ela separa D2 de D3 pela queda de AUC, mas este concept drift num segmento não derrubou a AUC. A árvore indicaria recalibrar (+US$ 571 mil), quando o conservador seguido de challenger rende mais. O playbook e o detector já usam a concentração em segmento; a árvore não.
2. **A6 está declarada como automática, mas não roda sozinha.** A regra P03 lista A6 como ação automática, porém o job só registra a recomendação. O challenger foi treinado manualmente, com as funções de `src/response/`.
3. **A rampa passou sem aviso.** A razão subiu de 1,06 para 1,19 sem nenhum alerta, e o primeiro alerta já veio em SEV-2. Não houve aviso antecipado, nem havia como, em L2 ou L3, porque é concept drift.
4. **A fila de revisão não está dimensionada.** O modo conservador mandou de 14% a 21% de cada lote para revisão manual (855 a 1.233 propostas por 6.000). Nem o RUNBOOK nem o ADR-0012 dizem qual capacidade a fila suporta, nem o que fazer quando estoura.
5. **A cegueira do operador foi só procedimental.** Quem operou o game day conhece o desenho dos cenários. A mitigação foi decidir só pela visão do operador (`make gameday-watch`) e abrir o manifesto apenas no fim, mas isso não equivale a um operador sem conhecimento prévio.

## Itens de ação

| # | Ação | Dono | Prazo | Status |
|---|---|---|---|---|
| 1 | Reescrever o ramo L4 da árvore §8.7 para separar D2 de D3 pela concentração em segmento, como o detector e o playbook já fazem | autor | F7 (7.11) | feito: triagem no [RUNBOOK](../RUNBOOK.md#triagem-de-um-alerta-árvore-de-decisão) |
| 2 | Decidir entre executar A6 no job (treino em sombra disparado pela regra) ou reclassificar A6 como humana, e documentar o comando no playbook | autor | F7 (7.11) | feito: A6 humana ([ADR-0022](../adr/0022-challenger-shadow-human.md)), `make gameday-shadow` |
| 3 | Avaliar um alerta de tendência da razão observado/esperado (subidas consecutivas abaixo do SEV-1), calibrado no S0 antes de entrar | autor | backlog | aberto; o estudo de robustez mede o custo de esperar o SEV-2 (+US$ 0,56 e +0,75 mi em 2 de 5 seeds do S2, [ROBUSTNESS.md](../ROBUSTNESS.md)) |
| 4 | Declarar a capacidade da fila de revisão e o comportamento quando ela estoura (ADR-0012 e RUNBOOK) | autor | F7 (7.11) | feito: 15% do lote, excedente recusado com R11 ([ADR-0021](../adr/0021-review-queue-capacity.md), [RUN-20261117-response-ALL-01](../runs/RUN-20261117-response-ALL-01.md)) |
| 5 | Ligar este incidente à análise causal (DAG e mecanismo) | autor | F8 (8.6) | feito: [CAUSAL_ANALYSIS.md](../CAUSAL_ANALYSIS.md), seção 6 |

> Postmortem sem culpa: o foco é o sistema, não as pessoas.
