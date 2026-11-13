# Model Card — credit-scoring (champion v1)

> **Status: rascunho (F2).** As seções de fairness e de sensibilidade a drift simulado são completadas nas fases F5 e F8. Todo número cita o RUN que o produziu.

## Identificação

| Item | Valor |
|---|---|
| Modelo | Regressão logística com calibração de Platt (sigmoid) |
| Registro | MLflow `credit-scoring` v1, alias `champion` |
| Treino | [RUN-20261112-train-REF-02](runs/RUN-20261112-train-REF-02.md) (árvore limpa, seed 42) |
| Dados | Referência = safra 2013 do Lending Club, aplicações individuais ([data card](data_card.md)) |
| Perfil de referência | `models/reference_profile.json` (artefato do mesmo run no MLflow) |
| Decisões | [ADR-0006](adr/0006-base-model.md) (modelo) e [ADR-0007](adr/0007-cost-threshold.md) (limiar) |

## Uso pretendido

Estimar a probabilidade de inadimplência (*charged off*/*default*) de uma proposta de empréstimo pessoal individual **no momento da concessão**, para apoiar a decisão aprovar/recusar com um limiar econômico. É o "paciente" do sistema de monitoramento deste projeto: o foco está em detectar e responder à sua degradação.

## Usos não pretendidos

- Decisão de crédito **totalmente automatizada sem revisão humana** de casos limítrofes. O modo conservador (F7) envia a faixa cinza para revisão, em linha com o direito de revisão de decisão automatizada (a confirmar na F8).
- Aplicações conjuntas, outros produtos de crédito ou populações fora da política de originação do credor de origem.
- Precificação: o modelo usa `int_rate` e `grade` como entrada e não pode ser usado para defini-los.
- Qualquer inferência sobre atributos protegidos.

## Entradas

33 features de originação (allowlist em `config/data/column_inventory.yaml`): condições do empréstimo (`loan_amnt`, `term`, `int_rate`, `installment`, `grade`, `purpose`), perfil do tomador (`annual_inc`, `emp_length`, `home_ownership`, `verification_status`, `dti`) e histórico de bureau (FICO, utilização, inquéritos, contas, tempo de histórico). Nenhuma coluna pós-concessão, nenhum identificador direto, nenhum texto livre.

## Desempenho ([RUN-20261112-train-REF-02](runs/RUN-20261112-train-REF-02.md))

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

0,33 (aprova se score < 0,33), escolhido por valor esperado com premissas de custo PROPOSTAS. No teste: aprovação de 94,3%, bad rate dos aprovados de 14,3% e US$ 445 por proposta (ADR-0007).

**Sensibilidade:** o limiar é **pouco robusto** às premissas. Com LGD entre 0,4 e 0,8 e realização de margem entre 0,3 e 0,7, o ótimo varia de 0,06 a 0,55 e a aprovação de 14% a 100% (notebook `02_modelagem`, seção 4).

**Validação contra o caixa realizado** ([RUN-20261113-calib-COST-01](runs/RUN-20261113-calib-COST-01.md)):

- As premissas medidas no dado são LGD 0,327 e realização de juros 0,756, menos pessimistas que as propostas.
- No teste, o limiar 0,33 tem **regret de 8,1%** frente ao ótimo realizado (0,555).
- Com as premissas empíricas, o modelo de custo reproduz o caixa real (Pearson 0,999 entre as curvas).
- Nesta população já filtrada pelo credor, recusar rende pouco enquanto o custo de funding fica abaixo de ~8% a.a.

A revisão do limiar está **proposta** no ADR-0016 e aguarda decisão.

## Sensibilidade a drift (observada fora do tempo)

- **Calibração degrada com o tempo, e o ranking se mantém.** Observado/esperado vai de 1,006 (2013) a 1,113 (2014) e 1,287 (2015), com AUC estável perto de 0,69–0,70. O modelo passa a **subestimar o risco**.
- **O score desloca:** PSI test → OOT 2015 = 0,2257, puxado pela queda de `int_rate`, a feature mais importante, sem queda correspondente de inadimplência.
- Implicação para o monitoramento: sinais L3 (PSI do score, bad rate esperado) acendem antes de qualquer perda de AUC. Recalibração (A5) é a resposta candidata natural para esse padrão (F7).

## Limitações

1. **Viés de seleção:** treinado só em empréstimos aprovados pelo credor. O risco dos recusados é desconhecido (*reject inference*).
2. **Rótulo maduro só até 2015–2016:** o desempenho em safras recentes não é mensurável no snapshot (mar/2019).
3. **Dependência da precificação do credor** (`int_rate`, `grade`): mudança de política de preço vira drift de score.
4. **Uma única safra de referência** (2013): sazonalidade e ciclo de um só ano.
5. **Premissas de custo PROPOSTAS:** o limiar é sensível a LGD e margem.

## Fairness

*Pendente (F8).* Atributos disponíveis para análise: `addr_state` (fora do modelo), `emp_length` e `home_ownership`. O dataset não tem gênero nem idade.

## Manutenção

Monitorado por lote mensal (F3–F6). Respostas à degradação, como recalibração, challenger, rollback e modo conservador, seguem a política de F7. Retreino só com rótulo maduro e dado aprovado no contrato (GR-7, GR-8).
