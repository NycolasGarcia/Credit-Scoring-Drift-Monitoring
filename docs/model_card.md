# Model Card — credit-scoring (champion v2)

> **Status: rascunho (F2).** As seções de fairness e de sensibilidade a drift simulado são completadas nas fases F5 e F8. Todo número cita o RUN que o produziu.

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

- Decisão de crédito **totalmente automatizada sem revisão humana** de casos limítrofes. O modo conservador (F7) envia a faixa cinza para revisão, em linha com o direito de revisão de decisão automatizada (a confirmar na F8).
- Aplicações conjuntas, outros produtos de crédito ou populações fora da política de originação do credor de origem.
- Precificação: o modelo usa `int_rate` e `grade` como entrada e não pode ser usado para defini-los.
- Qualquer inferência sobre atributos protegidos.

## Entradas

33 features de originação (allowlist em `config/data/column_inventory.yaml`): condições do empréstimo (`loan_amnt`, `term`, `int_rate`, `installment`, `grade`, `purpose`), perfil do tomador (`annual_inc`, `emp_length`, `home_ownership`, `verification_status`, `dti`) e histórico de bureau (FICO, utilização, inquéritos, contas, tempo de histórico). Nenhuma coluna pós-concessão, nenhum identificador direto, nenhum texto livre.

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

**Leitura:** a aprovação próxima de 100% em regime normal reflete o **viés de seleção**, porque os dados já passaram pela política do credor de origem. O valor do modelo aparece sob degradação, quando o modo conservador (GR-4, F7) usa o ranking para cortar a cauda de risco até o teto de bad rate dos aprovados (14%, PROPOSTO).

## Sensibilidade a drift (observada fora do tempo)

- **Calibração degrada com o tempo, e o ranking se mantém.** Observado/esperado vai de 1,006 (2013) a 1,113 (2014) e 1,287 (2015), com AUC estável perto de 0,69–0,70. O modelo passa a **subestimar o risco**.
- **O score desloca:** PSI test → OOT 2015 = 0,2257, puxado pela queda de `int_rate`, a feature mais importante, sem queda correspondente de inadimplência.
- Implicação para o monitoramento: sinais L3 (PSI do score, bad rate esperado) acendem antes de qualquer perda de AUC. Recalibração (A5) é a resposta candidata natural para esse padrão (F7).

## Limitações

1. **Viés de seleção:** treinado só em empréstimos aprovados pelo credor. O risco dos recusados é desconhecido (*reject inference*).
2. **Rótulo maduro só até 2015–2016:** o desempenho em safras recentes não é mensurável no snapshot (mar/2019).
3. **Dependência da precificação do credor** (`int_rate`, `grade`): mudança de política de preço vira drift de score.
4. **Uma única safra de referência** (2013): sazonalidade e ciclo de um só ano.
5. **Premissa de funding declarada (5% a.a.):** as perdas e margens são medidas, mas o custo de funding é política. Acima de ~8% a.a., o caixa realizado da carteira vira negativo e o limiar muda radicalmente (ADR-0016).

## Fairness

*Pendente (F8).* Atributos disponíveis para análise: `addr_state` (fora do modelo), `emp_length` e `home_ownership`. O dataset não tem gênero nem idade.

## Manutenção

Monitorado por lote mensal (F3–F6). Respostas à degradação, como recalibração, challenger, rollback e modo conservador, seguem a política de F7. Retreino só com rótulo maduro e dado aprovado no contrato (GR-7, GR-8).
