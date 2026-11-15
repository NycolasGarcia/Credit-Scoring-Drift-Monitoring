## Leitura

**A resposta certa depende do diagnóstico, e a matriz acerta qual é.** Valores contra "não fazer nada", com a revisão tratada como perda, salvo indicação.

- **D1, choque econômico (S1).**
  - **A política não age** (regra P09, só registrar), e é o certo: o modelo continua calibrado.
  - **Forçar respostas não compensa:** retreinar sem gate perderia US$ 109 mil, e recalibrar dá +US$ 69 mil, o que é ruído.
- **D3, concept drift (S2).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,94 mi**, com 17,4% das propostas em revisão.
  - **De onde vem o ganho:** a regra por valor sem correção de risco rende +US$ 0,51 mi. Portanto, cerca de 83% do ganho vem da correção pela razão observado/esperado.
  - **Alternativas de modelo:** recalibrar dá +US$ 0,57 mi. O challenger renderia +US$ 0,61 mi, mas o gate o reprovou por 1,55 p.p. de descalibração.
- **D2, prior shift (S3).**
  - **Resultado:** o modo conservador por valor rende **+US$ 2,66 mi**, e a recalibração, sozinha, **+US$ 0,87 mi**.
  - **Combinação:** a matriz recomenda as duas (A4 automático e A5 humano). O efeito combinado não foi simulado.
- **D6, bug de unidade (S4).**
  - **A política retém o lote e manda corrigir a fonte.**
  - **Custo da quarentena:** depende do que acontece com a fila. Se ela se perde, a quarentena custa US$ 1,72 mi; se é decidida depois do conserto, rende **+US$ 4,01 mi** contra decidir sobre o dado quebrado.
  - **A pior resposta seria o modo conservador:** forçado sobre o bug, perderia US$ 6,3 mi, porque o bug faz o modelo enxergar risco onde não há.

**O teto de 14% foi descartado com evidência** ([ADR-0019](adr/0019-conservative-mode-by-value.md)). Ele recusa empréstimos que continuam lucrativos: −US$ 1,25 mi no S2 e −US$ 2,95 mi no S3. Na carteira já aprovada pelo credor, o corte certo é o de valor esperado negativo, não um teto de bad rate.

**O gate de promoção é conservador por desenho.**
- **Rejeitou os quatro challengers do ponto de decisão.**
- **No S1, evitou uma perda de US$ 109 mil.**
- **Nos outros, deixou valor na mesa:** +US$ 0,61 mi no S2, +US$ 0,26 mi no S3 e +US$ 1,47 mi no S4.
- **No ponto de decisão quase não há rótulo maduro do regime novo** (atraso de 3 lotes), então retreinar cedo é uma aposta. O gate a recusa enquanto o challenger não prova calibração.

**Retreinar sobre o bug parece bom, e por isso é perigoso.** Enquanto o bug persiste, o challenger treinado no dado quebrado rende +US$ 1,2 mi, porque aprende a descontar a renda corrompida. É exatamente o modo como o retreino esconde um defeito de dado: quando a fonte for corrigida, esse modelo estará calibrado para um dado que não existe mais. Este cenário não mede esse segundo momento. A regra GR-7 e a precedência do D6 existem para não chegar lá.

**Premissas que limitam a leitura:**
- **Horizonte curto:** de 4 a 7 lotes após o ponto de decisão.
- **Custo da equipe de revisão não modelado.**
- **Revisão em dois extremos:** perdida, ou decidida depois como o champion decidiria. No modo por valor, decidir depois "como o champion" anula o ganho; o ganho exige que a revisão confirme a recusa dos casos de valor negativo.
- **Cenários simulados:** os desfechos vêm do oráculo do [ADR-0017](adr/0017-scenario-simulator.md).
