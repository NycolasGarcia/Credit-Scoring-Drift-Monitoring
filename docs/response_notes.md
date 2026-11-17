## Leitura

**A resposta certa depende do diagnóstico, e a matriz acerta qual é.** Valores contra "não fazer nada", com a revisão tratada como perda, salvo indicação.

- **D1, choque econômico (S1).**
  - **A política não age** (regra P09, só registrar), e é o certo: o modelo continua calibrado.
  - **Forçar respostas não compensa:** retreinar sem gate perderia US$ 109 mil, e recalibrar dá +US$ 69 mil, o que é ruído.
- **D3, concept drift (S2).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,94 mi**, com 14,6% das propostas em revisão (fila limitada a 15% do lote, [ADR-0021](adr/0021-review-queue-capacity.md)).
  - **De onde vem o ganho:** a regra por valor sem correção de risco rende +US$ 0,51 mi. Portanto, cerca de 83% do ganho vem da correção pela razão observado/esperado.
  - **Alternativas de modelo:** recalibrar dá +US$ 0,57 mi. O challenger passa no gate com calibração relativa ([ADR-0020](adr/0020-relative-calibration-gate.md)) e rende +US$ 0,61 mi a partir do lote seguinte.
- **D2, prior shift (S3).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,66 mi** (15,0% em revisão), e a recalibração, sozinha, **+US$ 0,87 mi**.
  - **Combinação:** a matriz recomenda as duas (A4 automático e A5 humano). O efeito combinado não foi simulado.
- **D6, bug de unidade (S4).**
  - **A política retém o lote e manda corrigir a fonte.**
  - **Custo da quarentena:** depende do que acontece com a fila. Se ela se perde, a quarentena custa US$ 1,72 mi; se é decidida depois do conserto, rende **+US$ 4,01 mi** contra decidir sobre o dado quebrado.
  - **A pior resposta seria o modo conservador:** forçado sobre o bug, perderia US$ 6,3 mi, porque o bug faz o modelo enxergar risco onde não há.

**O teto de 14% foi descartado com evidência** ([ADR-0019](adr/0019-conservative-mode-by-value.md)). Ele recusa empréstimos que continuam lucrativos: −US$ 1,25 mi no S2 e −US$ 2,95 mi no S3. Na carteira já aprovada pelo credor, o corte certo é o de valor esperado negativo, não um teto de bad rate.

**O gate de promoção separa os casos.**
- **Aprovou o challenger do S2** (concept drift), que rende +US$ 0,61 mi.
- **No S1, evitou uma perda de US$ 109 mil.**
- **No S3, deixou US$ 0,26 mi na mesa:** em prior shift, a resposta indicada é recalibrar (+US$ 0,87 mi), não retreinar.
- **No S4, recusou o challenger treinado sobre o bug,** que rende +US$ 1,47 mi só enquanto o bug persiste (ver abaixo).
- **No ponto de decisão quase não há rótulo maduro do regime novo** (atraso de 3 lotes), então retreinar cedo é uma aposta. O gate só aceita quando o challenger supera o champion na ordenação e na calibração.

**Retreinar sobre o bug parece bom, e por isso é perigoso.** Enquanto o bug persiste, o challenger treinado no dado quebrado rende +US$ 1,2 mi, porque aprende a descontar a renda corrompida. É exatamente o modo como o retreino esconde um defeito de dado: quando a fonte for corrigida, esse modelo estará calibrado para um dado que não existe mais. Este cenário não mede esse segundo momento. A regra GR-7 e a precedência do D6 existem para não chegar lá.

**Premissas que limitam a leitura:**
- **Horizonte curto:** de 4 a 7 lotes após o ponto de decisão.
- **Custo da equipe de revisão não modelado.**
- **Revisão em dois extremos:** perdida, ou decidida depois como o champion decidiria.
  - **Sem teto de fila:** decidir depois "como o champion" anulava o ganho, porque o champion aprova de volta toda a faixa de valor negativo.
  - **Com o teto de 15% ([ADR-0021](adr/0021-review-queue-capacity.md)):** o excedente de pior valor esperado é recusado na hora, e o ganho sobrevive mesmo nesse extremo: +US$ 1,07 mi no S2 e +US$ 2,13 mi no S3.
- **Cenários simulados:** os desfechos vêm do oráculo do [ADR-0017](adr/0017-scenario-simulator.md).
