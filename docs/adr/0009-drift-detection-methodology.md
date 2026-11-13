# ADR-0009 — Metodologia de detecção de drift

- **Status:** aceito
- **Data:** 2026-11-13
- **Fase:** F5

## Contexto

O detector precisa apontar variáveis degradadas com um relatório do Evidently (R2), sem alarmar à toa e sem confundir tipos de degradação (§8.2). Três fatos pesam:

1. **N grande torna o p-valor inútil como gatilho.** Com uma referência de ~107 mil linhas e lotes de 6 mil a 45 mil, qualquer diferença irrelevante fica "significativa" (NV-10).
2. **O PSI embutido do Evidently 0.7.23 não serve como gatilho**, conforme o código-fonte da versão fixada (`legacy/calculations/stattests/psi.py` e `utils.get_binned_data`):
   - ele faz bins de **largura igual** (regra de Sturges) **sobre referência e lote atual juntos**, então o lote atual define os próprios bins;
   - em variáveis de cauda pesada, como `annual_inc` (máximo de US$ 10 milhões), quase toda a massa cai num bin e o PSI fica cego.
   Também do código-fonte: o teste padrão implícito para mais de 1.000 linhas é a distância de Wasserstein, e os nulos são descartados antes de qualquer teste.
3. **Rótulo atrasado.** O desempenho com rótulo (L4) só existe meses depois. Concept drift puro (S2) não aparece nas entradas.

## Decisão

1. **Gatilho de L2: PSI com bins fixos da referência.** São 10 decis da partição de referência, mais um bin de nulos e um bin `__other__` para categorias novas, com ε = 1e-4, todos congelados no `reference_profile.json` e nunca recalculados.
   - **Registrados, mas nunca gatilho:** o p-valor do KS (numéricas), o do χ² (categóricas) e a distância de Wasserstein normalizada.
2. **API do Evidently usada (0.7.23, NV-8 fechado):**
   - **Relatório:** `from evidently import Report, Dataset, DataDefinition` e `from evidently.presets import DataDriftPreset`, executado com `Report([DataDriftPreset(columns, method, threshold)]).run(atual, referência)`. O valor de cada coluna é lido de `snapshot.dict()["metrics"]` (`ValueDrift`), e o HTML sai por `snapshot.save_html`.
   - **Teste explícito por coluna:** o teste `psi_ref` (PSI com bins da referência, a mesma regra do perfil) é registrado em `evidently.legacy.calculations.stattests.registry.register_stattest`. Nenhuma coluna usa o teste padrão implícito.
   - **Equivalência verificada por teste:**
     - o `psi_ref` dentro do Evidently é igual ao PSI próprio, com diferença menor que 1e-9, nas colunas sem nulos;
     - o KS e o Wasserstein embutidos do Evidently batem com o scipy e com a implementação própria.
3. **Camadas e sinais por lote mensal:**

   | Camada | Sinal | Direção |
   |---|---|---|
   | L2 | PSI por feature | quanto maior, pior |
   | L3 | PSI do score (decis do teste) | quanto maior, pior |
   | L3 | Variação da aprovação em p.p. | bilateral |
   | L4 | Razão observado/esperado | simétrica: max(r, 1/r) |
   | L4 | Queda de AUC versus a referência | só piora conta; AUC que melhora não alerta |

   A L4 avalia, no lote `t`, exatamente os rótulos que se tornam observáveis em `t` (`label_batch == t`), com no mínimo 500 rótulos.
4. **Múltiplas comparações:**
   - **SEV-1:** basta uma feature, qualquer uma.
   - **SEV-2:** exige uma feature do top-10 de importância.
   - **SEV-3:** exige três features do top-10.
   - **Calibração:** o corte SEV-1 de cada um dos 5 sinais de alerta usa o quantil nulo `1 − 5%/5`, uma correção de Bonferroni sobre os sinais.
5. **Calibração no controle (caixa 5.6):**
   - **Bootstrap:** 500 lotes A/A de 6.000 propostas sorteadas do holdout. É o menor lote simulado, portanto o de ruído máximo.
   - **Regra de calibração:**
     - SEV-1 = max(proposto, quantil nulo);
     - SEV-2 = max(proposto, logo acima do máximo nulo);
     - SEV-3 = max(proposto, SEV-2).
   - **Convenção como piso:** os valores de mercado (0,10 e 0,25) nunca são baixados. A calibração só sobe um corte quando o controle mostra falso alarme.
6. **Diagnóstico (§8.7):**
   - **D6:**
     - **Assinatura:** um excesso de valores abaixo do percentil 1 da referência que, multiplicados por um fator de unidade (12, 52, 100 ou 1.000), devolvem a distribuição à referência, cortando o PSI pelo menos pela metade.
     - **Precedência:** vem antes de qualquer diagnóstico de modelo.
   - **D3 × D2:** usa a amplitude do descolamento observado/esperado (em logit) entre quintis das features do top-10. Descolamento concentrado num segmento indica D3; descolamento uniforme indica D2.
7. **Relatório por cenário:** um HTML do Evidently cobrindo a janela que o próprio detector escolhe: do primeiro alerta em diante, ou os últimos 6 lotes se nada alertou. Nunca é o ground truth que escolhe a janela.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| p-valor do KS/χ² como gatilho | Padrão estatístico conhecido | Com N grande, rejeita diferenças irrelevantes (medido em S5, ver DRIFT_EVALUATION) | Gatilho por tamanho de efeito |
| PSI embutido do Evidently | Zero código próprio | Bins de largura igual sobre referência e lote atual juntos; cego em cauda pesada; o lote define os bins | Viola a regra dos bins fixos (§8.3) |
| Teste padrão do Evidently (escolha automática) | Simples | Implícito (Wasserstein acima de 1.000 linhas); o relatório não diria qual teste gerou o veredito | §4, regra 2: teste explícito por coluna |
| Wasserstein normalizada como gatilho | Tamanho de efeito; sem bins | Normaliza pelo desvio-padrão, que outliers inflam em `annual_inc`; sem convenção de mercado para o corte | Registrada como evidência, não como gatilho |
| Alibi Detect | Testes multivariados (MMD) | Segunda biblioteca; R2 cita o Evidently nominalmente; multivariado não aponta a variável | Fora do escopo da rubrica |
| Recalcular os bins a cada lote | Bins "atuais" | O PSI passa a medir nada (§11.8) | — |

## Consequências

**Boas:**
- **Mesmo número no relatório e no código:** a regra de bins é uma só, e o PSI do HTML do Evidently é o mesmo número que dispara o alerta (testado).
- **Separação limpa:** D1 × D3 × D2 × D6 se distinguem com sinais que existem em produção, sem olhar o manifesto.
- **Falso alarme conhecido:** o falso alarme de cada sinal é medido, não suposto.

**Ruins / custos aceitos:**
- **Nulos fora do relatório:** o Evidently descarta nulos, então o HTML não mostra mudança de taxa de nulos. Essa mudança aparece no PSI próprio (bin de nulos) e na regra S01 do contrato.
- **PSI do score fora do cruzamento exato:** no relatório, o score usa bins da partição de referência inteira; no alerta, usa os decis do conjunto de teste.
- **Convenção conservadora:** o PSI de 0,10 fica cerca de 20× acima do ruído de um lote de 6.000. O detector é conservador por escolha, porque drift não é degradação (§8.1). Um corte menor detectaria o S1 mais cedo, ao custo de alertar para mudanças irrelevantes.
- **Calibração na escala do lote simulado:** ela foi feita com lotes de 6.000. Lotes reais maiores (S5) têm menos ruído, então os cortes valem com folga.

## Como saberemos que a decisão estava errada

- **Falso alarme acima da meta:** os lotes reais do S0 alarmam acima da meta (5% em SEV-1, 0% em SEV-2), ou uma recalibração com outra seed muda os cortes.
- **Cruzamento falha:** o `psi_ref` do Evidently diverge do PSI próprio em coluna sem nulos (o teste quebra), ou uma atualização do Evidently muda a API de registro de testes.
- **Detector cego no S5:** o desempenho cai com rótulo maduro sem nenhum sinal de L2/L3 que o anteceda. Nesse caso, o detector de entrada estaria cego a algo que importa.

## Referências

- Código da versão fixada: `evidently/legacy/calculations/stattests/{psi,ks_stattest,wasserstein_distance_norm,utils,registry}.py`, `evidently/presets/drift.py`
- `src/monitoring/` (drift, output, performance, severity, diagnosis, calibration, evidently_report, detect, evaluation)
- [THRESHOLDS.md](../THRESHOLDS.md), [DRIFT_EVALUATION.md](../DRIFT_EVALUATION.md), [ADR-0017](0017-scenario-simulator.md)
