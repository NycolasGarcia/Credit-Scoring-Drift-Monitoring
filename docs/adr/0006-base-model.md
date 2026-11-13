# ADR-0006 — Modelo base: regressão logística calibrada como champion v1

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F2

## Contexto

O projeto precisa de um classificador simples, honesto e calibrado. O monitoramento compara o bad rate **esperado** (média do score) com o **observado**, e essa comparação só tem sentido com probabilidades calibradas. Entre modelos equivalentes, o critério de desempate é a **estabilidade** do score fora do tempo, porque instabilidade vira alarme em produção.

Candidatos treinados na referência 2013 (train 70% / calibração 15% / teste 15%, estratificado por safra × alvo, seed 42). CV estratificada de 5 folds no train. Avaliação fora do tempo (OOT) nas safras 2014 e 2015 maduras. Comparação completa em [EXPERIMENTS.md](../EXPERIMENTS.md).

| Métrica | Dummy ([REF-01](../runs/RUN-20261112-train-REF-01.md)) | LogReg ([REF-02](../runs/RUN-20261112-train-REF-02.md)) | XGBoost ([REF-03](../runs/RUN-20261112-train-REF-03.md)) |
|---|---|---|---|
| AUC CV (train) | 0,5000 | 0,6989 ± 0,0064 | 0,7009 ± 0,0068 |
| AUC test | 0,5000 | **0,7001** | 0,6979 |
| KS test | 0,0000 | 0,3032 | 0,2998 |
| Brier test (pré → pós calibração) | 0,1316 | 0,12253 → 0,12254 | 0,12266 → 0,12290 |
| AUC OOT 2014 / 2015 | 0,50 / 0,50 | 0,6907 / 0,6954 | 0,6903 / 0,6928 |
| PSI do score test → OOT 2015 | — | **0,2257** | 0,2380 |

## Decisão

1. **Champion v1 = regressão logística** em `Pipeline` com imputação por mediana e indicadores de nulo, `log1p` nos valores monetários, padronização e one-hot nas categóricas, **calibrada por Platt** (sigmoid). Registrada no MLflow como `credit-scoring` v1, alias `champion`.
2. **Regra de seleção** (`select_champion`, testada):
   - todo candidato precisa superar o Dummy no AUC de teste;
   - vence o maior AUC;
   - diferenças até 0,005 (PROPOSTO) contam como empate, e no empate vence o menor PSI do score fora do tempo.

   LogReg e XGBoost empataram (Δ = 0,0022), e a LogReg venceu pela estabilidade.
3. **Calibração é sempre ajustada e reportada.** O método é escolhido por Brier num subconjunto da calibração separado do teste. Resultado: a calibração foi **neutra** para a LogReg (+1,5×10⁻⁶ de Brier no teste, sigmoid escolhido por margem de 1,6×10⁻⁷) e **prejudicial** para o XGBoost (isotônica +2,4×10⁻⁴). A regressão logística já é bem calibrada por construção: bad rate esperado de 15,50% contra observado de 15,58% no teste.
4. **Infraestrutura MLflow 3.18:**
   - tracking em SQLite (`mlruns/mlflow.db`, backend padrão desta versão);
   - modelos serializados com **skops** e uma **lista explícita de tipos confiáveis** (`config/models/training.yaml`), em vez de pickle, que executa código arbitrário ao carregar. Um teste garante que a lista basta para carregar os modelos calibrados.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| XGBoost calibrado | AUC CV ligeiramente maior | Empate no teste; menos estável no OOT; isotônica piorou o Brier; menos explicável | Perde no desempate de estabilidade |
| XGBoost sem calibração | Brier test 0,12266 | Viola a regra de calibração obrigatória; continua menos estável | Idem |
| Ajuste de hiperparâmetros | Talvez +0,005 a +0,01 de AUC | Custo de tempo; o modelo é o paciente, não o produto | Fora do foco do projeto |
| Serialização por pickle/cloudpickle | Sem lista de tipos | Carregar modelo executa código arbitrário | Risco de segurança desnecessário |

## Consequências

**Boas:**
- Modelo explicável no estilo scorecard: coeficientes por feature e importância por permutação liderada por `int_rate`, `term`, `annual_inc` e `loan_amnt`.
- Calibrado na referência.
- Estável o suficiente para ser monitorado.

**Ruins / custos aceitos:**
- O portão PROPOSTO "Brier pós ≤ pré" **não passa** formalmente: a diferença de 1,5×10⁻⁶ é ruído. O resultado está registrado no PROGRESS da F2, com a proposta de reformular o portão como |esperado − observado| ≤ 1 pp no teste, que hoje dá 0,08 pp.
- `int_rate` e `grade` são saídas da precificação do próprio credor. O modelo aprende parte do risco por meio do preço, e a queda de juros em 2015 desloca o score para baixo sem que o risco tenha caído. Isso é a principal fonte do drift de score no OOT.

**Achado de degradação natural** (notebook `02_modelagem`, mesmo champion): a razão observado/esperado vai de 1,006 (teste) a 1,113 (OOT 2014) e 1,287 (OOT 2015). O AUC se mantém em torno de 0,69–0,70. É perda de calibração com o ranking preservado, já visível fora do tempo e antes de qualquer simulação.

## Como saberemos que a decisão estava errada

- No monitoramento (F5), o PSI do score da LogReg disparar mais falsos alarmes em S0 do que o alvo.
- Um challenger não linear superar o champion em mais de 0,005 de AUC na janela madura recente, mantendo estabilidade e calibração (gate GR-5, F7).
