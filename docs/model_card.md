# Model Card — credit-scoring (champion v2)

> **Status: final (F8).** Todo número cita o RUN que o produziu. Projeto acadêmico: o modelo não decide crédito de ninguém; "produção" é simulada ([GOVERNANCE.md](GOVERNANCE.md)).

## Identificação

| Item | Valor |
|---|---|
| Modelo | Regressão logística com calibração de Platt (sigmoid) |
| Registro | MLflow `credit-scoring` v2, alias `champion`. Mesmo modelo do v1; muda o limiar (ADR-0016) |
| Treino | [RUN-20261113-train-REF-02](runs/RUN-20261113-train-REF-02.md) (árvore limpa, seed 42); v1 em [RUN-20261112-train-REF-02](runs/RUN-20261112-train-REF-02.md) |
| Dados | Referência = safra 2013 do Lending Club, aplicações individuais ([data card](data_card.md)) |
| Perfil de referência | `models/reference_profile.json` (artefato do mesmo run no MLflow) |
| Decisões | [ADR-0006](adr/0006-base-model.md) (modelo) e [ADR-0016](adr/0016-empirical-cost-threshold.md) (limiar; supersede o 0007) |

## Uso pretendido

Estimar a probabilidade de inadimplência (*charged off*/*default*) de uma proposta de empréstimo pessoal individual **no momento da concessão**, para apoiar a decisão aprovar/recusar com um limiar econômico. É o "paciente" do sistema de monitoramento deste projeto: o foco está em detectar e responder à sua degradação.

## Usos não pretendidos

- **Decisão de crédito real.** É um trabalho acadêmico, sem validação regulatória nem revisão jurídica.
- Decisão de crédito **totalmente automatizada sem revisão humana** de casos limítrofes. O modo conservador envia a faixa limítrofe para revisão (motivo R10), além do mínimo do direito de revisão de decisão automatizada (LGPD art. 20; Lei 12.414/2011, art. 5º, VI; [ADR-0014](adr/0014-privacy-legal-basis-retention.md)).
- Aplicações conjuntas, outros produtos de crédito ou populações fora da política de originação do credor de origem.
- Precificação: o modelo usa `int_rate` e `grade` como entrada e não pode ser usado para defini-los.
- Qualquer inferência sobre atributos protegidos.

## Entradas

33 features de originação (allowlist em `config/data/column_inventory.yaml`): condições do empréstimo (`loan_amnt`, `term`, `int_rate`, `installment`, `grade`, `purpose`), perfil do tomador (`annual_inc`, `emp_length`, `home_ownership`, `verification_status`, `dti`) e histórico de bureau (FICO, utilização, inquéritos, contas, tempo de histórico). Nenhuma coluna pós-concessão, nenhum identificador direto, nenhum texto livre.

O modelo só pontua lotes aprovados pelo contrato de dados ([DATA_CONTRACTS.md](DATA_CONTRACTS.md), [ADR-0008](adr/0008-data-contracts.md)): lote com falha estrutural ou com mais de 1% de linhas inválidas é bloqueado sem pontuação; linhas inválidas isoladas vão para quarentena. A saída (score em [0, 1], decisão coerente com o limiar) também é validada.

## Desempenho ([RUN-20261112-train-REF-02](runs/RUN-20261112-train-REF-02.md); idêntico no v2, [RUN-20261113-train-REF-02](runs/RUN-20261113-train-REF-02.md))

| Conjunto | n | AUC | Gini | KS | PR-AUC | Brier | Bad rate esperado | Bad rate observado |
|---|---|---|---|---|---|---|---|---|
| CV train (5 folds) | — | 0,6989 ± 0,0064 | — | — | — | — | — | — |
| Teste (2013) | 16.177 | 0,7001 | 0,4002 | 0,3032 | 0,2931 | 0,1225 | 15,50% | 15,58% |
| OOT 2014 (maduro) | 175.509 | 0,6907 | 0,3814 | 0,2801 | 0,2691 | 0,1178 | 13,15% | 14,63% |
| OOT 2015 (maduro) | 282.787 | 0,6954 | 0,3907 | 0,2853 | 0,2720 | 0,1204 | 11,56% | 14,88% |

Baseline Dummy: AUC 0,5000 ([RUN-20261112-train-REF-01](runs/RUN-20261112-train-REF-01.md)).

## Calibração

Calibrado na referência (observado/esperado = 1,006 no teste). A recalibração de Platt foi neutra (ADR-0006). Curva de calibração em `notebooks/02_modelagem.ipynb`.

## Limiar de decisão

**0,495** (aprova se score < 0,495), escolhido por valor esperado ([ADR-0016](adr/0016-empirical-cost-threshold.md)).

Premissas:
- **medidas no caixa realizado** ([RUN-20261113-calib-COST-02](runs/RUN-20261113-calib-COST-02.md)): LGD 0,327, realização de juros dos bons 0,756 e dos maus 0,564;
- **declarada:** custo de funding de 5% a.a.

No teste ([RUN-20261113-train-REF-02](runs/RUN-20261113-train-REF-02.md)): aprovação de 99,8%, bad rate dos aprovados de 15,5% e US$ 942 por proposta. O limiar do F1 (0,195) aprovaria 71,5% com bad rate de 10,5% e US$ 547.

**Validação contra o caixa realizado** ([RUN-20261113-calib-COST-03](runs/RUN-20261113-calib-COST-03.md)): regret de 0,88% frente ao ótimo realizado e aderência de 0,9986 entre curvas modelada e realizada.

**Histórico:** o v1 usava 0,33 com premissas propostas (LGD 0,60; margem 0,50). Esse limiar tinha regret de 8,1% no caixa bruto ([RUN-20261113-calib-COST-01](runs/RUN-20261113-calib-COST-01.md)) e era pouco robusto: com as premissas variando na faixa plausível, o ótimo ia de 0,06 a 0,55.

**Leitura:** a aprovação próxima de 100% em regime normal reflete o **viés de seleção**, porque os dados já passaram pela política do credor de origem. O valor do modelo aparece sob degradação: o modo conservador usa o ranking para reter as propostas de valor esperado não positivo com o risco corrigido pela última razão observado/esperado ([ADR-0019](adr/0019-conservative-mode-by-value.md)). O teto de bad rate de 14% foi descartado por destruir valor.

## Sensibilidade a drift

**Fora do tempo (dado real):**
- **Calibração degrada, ranking se mantém.** Observado/esperado vai de 1,006 (2013) a 1,113 (2014) e 1,287 (2015) nos empréstimos maduros, com AUC estável perto de 0,69–0,70. No monitoramento da produção natural, a razão das coortes que vencem em 2017–2018 sobe de 1,03 para 1,39, com AUC entre 0,67 e 0,71 ([RUN-20261113-monitor-S5-02](runs/RUN-20261113-monitor-S5-02.md)). O modelo passa a **subestimar o risco**, um padrão de recalibração (A5, F7).
- **O score quase não desloca:** PSI mensal do score ≤ 0,078 em 2014–2018, mesmo com drift de entrada desde 2014 (`verification_status`, `int_rate`). O valor de 0,2257 registrado na F2 era um artefato do filtro de maturação (errata no [ADR-0006](adr/0006-base-model.md)).

**Cenários controlados** ([DRIFT_EVALUATION.md](DRIFT_EVALUATION.md)):
- **Choque econômico (S1):** score e risco sobem juntos e o modelo continua calibrado. Drift sem degradação.
- **Concept drift (S2) e prior shift (S3):** o bad rate sobe de 5 a 7 p.p. sem nenhum sinal nas entradas ou no score. Só o desempenho com rótulo maduro revela o problema, com o atraso do rótulo.
- **Bug de unidade (S4):** a renda mensal no lugar da anual derruba a aprovação em 6 p.p. e a AUC em até 0,05. O modelo é sensível a erro de unidade em `annual_inc`, sua 3ª feature mais importante.

**Limites de detecção** (5 seeds novos e 4 magnitudes, [RUN-20261117-calib-ROBUST-02](runs/RUN-20261117-calib-ROBUST-02.md)):
- **Na magnitude oficial,** os quatro mecanismos são detectados em 5 de 5 seeds, sem nenhum falso alarme no controle.
- **Passam sem detecção:** o concept drift com metade da intensidade (logit +0,5 no segmento) e o bug de unidade em 7,5% das linhas. O bug em 15% das linhas já é reconhecido como D6.
- **No concept drift,** quando o primeiro alerta chega cedo, ainda na rampa, ele pode ser lido como prior shift por um lote.

## Limitações

1. **Viés de seleção:** treinado só em empréstimos aprovados pelo credor. O risco dos recusados é desconhecido (*reject inference*).
2. **Rótulo maduro só até 2015–2016:** o desempenho em safras recentes não é mensurável no snapshot (mar/2019).
3. **Dependência da precificação do credor** (`int_rate`, `grade`): mudança de política de preço vira drift de score.
4. **Uma única safra de referência** (2013): sazonalidade e ciclo de um só ano.
5. **Premissa de funding declarada (5% a.a.):** as perdas e margens são medidas, mas o custo de funding é política. Acima de ~8% a.a., o caixa realizado da carteira vira negativo e o limiar muda radicalmente (ADR-0016).

## Resposta à degradação

Medida nos cenários com desfecho conhecido. Valores contra não fazer nada, mediana e faixa em 5 seeds novos ([RUN-20261117-calib-ROBUST-02](runs/RUN-20261117-calib-ROBUST-02.md)):

| Cenário | Resposta da política | Valor | Alternativa de modelo |
|---|---|---|---|
| Choque econômico (S1) | só registrar (o modelo continua calibrado) | 0 | retreinar sem gate perde em 4 de 5 seeds; o gate recusa os 5 |
| Concept drift (S2) | modo conservador | +US$ 2,09 mi (1,84 a 2,75) | recalibrar +0,46 mi (5/5); retreinar com gate de 0 a +0,58 mi (gate aprova em 3/5) |
| Prior shift (S3) | modo conservador + recalibrar (humano) | +US$ 2,23 mi (2,18 a 2,36) | recalibrar +0,27 mi (0,05 a 0,67) |
| Bug de unidade (S4) | quarentena e corrigir a fonte | — | forçar o modo conservador perderia de 6,25 a 6,77 mi |

Decisões: [ADR-0012](adr/0012-guardrails-conservative-mode.md), [ADR-0013](adr/0013-retraining-gate-rollback.md), [ADR-0019](adr/0019-conservative-mode-by-value.md), [ADR-0020](adr/0020-relative-calibration-gate.md), [ADR-0021](adr/0021-review-queue-capacity.md) e [ADR-0022](adr/0022-challenger-shadow-human.md). Game day e postmortem: [INC-0001](incidents/0001-s2-concept-drift-dti.md).

## Fairness

Detalhes em [FAIRNESS.md](FAIRNESS.md) ([RUN-20261117-fairness-ALL-01](runs/RUN-20261117-fairness-ALL-01.md)) e no [ADR-0015](adr/0015-bias-mitigation.md). O dataset não tem gênero nem idade; os grupos disponíveis são `home_ownership`, faixas de `emp_length` e `addr_state` (este fora do modelo).

- **Regime normal:** gap de aprovação entre grupos abaixo de 0,3 p.p. em todos os segmentos. Calibração por grupo entre 0,95 e 1,09 em `home_ownership` e `emp_length`. A AUC é menor em RENT (0,68) do que em MORTGAGE (0,71).
- **Modo conservador sem mitigação:** o corte cai mais sobre quem aluga (13 a 19 p.p. a menos de aprovação, em média) e sobre quem não informou o tempo de emprego (cerca de 40 p.p.).
- **Mitigação:** nenhum grupo de `home_ownership` ou `emp_length` fica mais de 7 p.p. abaixo do mais aprovado (motivo R12). Custa 7% do ganho do modo conservador no S2 e 4% no S3.
- **Gap regional:** só monitorado. Na produção natural, com o modo conservador ativo, ele cresce de 6 a 11 p.p. e dispara o alerta de fairness ([RUN-20261117-monitor-S5-01](runs/RUN-20261117-monitor-S5-01.md)).

## Manutenção

Monitorado por lote mensal: contrato de dados, drift de entrada e de score, desempenho com rótulo maduro e fairness por grupo, com alertas e playbooks ([RUNBOOK.md](RUNBOOK.md)). As respostas à degradação seguem a matriz de `config/response/policy.yaml`. Retreino só com rótulo maduro e dado aprovado no contrato (GR-7, GR-8), e promoção só pelo gate (GR-5), com rollback em um comando (GR-6). Retenção dos dados e artefatos no [plano de governança](GOVERNANCE.md).
