## Leitura

Os números dos cenários oficiais vêm de um seed por cenário. Este estudo repete cada cenário com 5 seeds novos e 4 magnitudes, com a regra de leitura declarada antes da execução (commit `c85d34b`, anterior a qualquer resultado).

Uma primeira execução completa foi descartada antes do commit: o veredito do RUN aplicava ao controle (S0) o critério de detecção, que não vale para ele. Os números eram idênticos aos desta.

### O que se sustenta

- **Nenhum falso alarme.**
  - No controle, 0 de 60 lotes em SEV-1 ou acima.
  - Antes do início do drift, 0 lotes em SEV-2 em todas as 80 variantes.
- **Detecção na magnitude oficial: 5 de 5 seeds nos quatro cenários.**
  - Atraso mediano até o SEV-2: 4 lotes no S1, 6 no S2, 3 no S3 e 0 no S4.
  - No S2, o atraso varia de 5 a 6 lotes: rótulo de 3 lotes, mais a rampa.
- **Diagnóstico na magnitude oficial:**
  - **S1, S3 e S4:** certo em todos os lotes alertados (35/35, 25/25 e 35/35).
  - **S2:** 19 de 20.
- **As respostas mantêm o sinal em todos os seeds.**
  - **Modo conservador por valor (política):** rende entre US$ 2,02 e 2,86 mi no S2 e entre US$ 2,38 e 2,67 mi no S3.
  - **Forçado sobre o bug do S4:** perde entre US$ 6,25 e 6,75 mi.
  - **Recalibrar:** ganha em todos os seeds do S2 e do S3.
  - **Gate:** nunca deixou o retreino perder valor (mínimo de US$ 0 com gate). No S1, recusou os 5 challengers, e retreinar sem gate perderia em 4 de 5.
- **A armadilha do retreino sobre o bug também é robusta:** rende entre +US$ 0,76 e +1,30 mi em todos os seeds enquanto o bug persiste. Só a precedência do D6 e a trava GR-7 impedem esse caminho.

### O que muda na leitura anterior

1. **O S2 falha a regra de diagnóstico declarada.**
   - **Números:** 19 de 20 lotes certos, com limite inferior de Wilson de 76%, abaixo dos 80% da regra.
   - **O erro:** no seed 303, o primeiro alerta veio no lote 7, em SEV-1, ainda na rampa. Ali o descolamento ainda não estava concentrado no segmento e foi lido como D2. Do lote 8 em diante, o diagnóstico é D3.
   - **Consequência operacional:** um lote com a recomendação humana errada (regra P06, recalibrar). Nenhuma ação automática errada, porque a P06 não aciona o modo conservador.
   - **Leitura correta:** "diagnóstico certo em todos os lotes" vale para o seed oficial. Em seeds novos, o D3 pode ser lido como D2 no primeiro alerta, quando ele chega cedo, em SEV-1.
2. **Os valores do seed oficial ficaram no lado favorável.**
   - **Modo conservador no S2:** +US$ 2,94 mi no oficial, acima de todos os seeds novos (mediana de 2,19 mi).
   - **Recalibração no S3:** +US$ 0,87 mi no oficial, acima do máximo dos seeds novos (mediana de 0,27 mi, faixa de 0,05 a 0,67 mi).
   - **O que citar:** a mediana e a faixa, não o valor de um seed.
3. **A política deixa valor na mesa quando o SEV-2 atrasa.**
   - **Onde:** nos seeds 302 e 303 do S2, o primeiro sinal de L4 (SEV-1) chegou um e dois lotes antes do SEV-2.
   - **Quanto:** forçar o modo conservador desde esse sinal renderia +US$ 0,56 e +0,75 mi a mais.
   - **Por que a regra não muda agora:** é o tema do item de ação 3 do [INC-0001](incidents/0001-s2-concept-drift-dti.md) (aviso na rampa). O controle sem nenhum SEV-1 sugere que agir em SEV-1 no L4 custaria pouco em falso alarme, mas a mudança exige decisão própria, com regra declarada antes.
4. **Retreinar com gate é instável no S2.** O gate aprovou o challenger em 3 de 5 seeds, então o ganho vai de US$ 0 a +0,58 mi. A resposta de modelo mais estável no S2 é recalibrar (5 de 5 com ganho).

### Limites de sensibilidade (magnitudes abaixo da oficial)

| Mecanismo | Detectado | Não detectado |
|---|---|---|
| Choque econômico (S1) | Em m = 0,5, só SEV-1 (5/5), com diagnóstico D1 certo. A política não age no D1, então isso basta | Em m = 0,25, nada |
| Concept drift (S2) | — | Logit +0,5 no segmento (m = 0,5) passa: 1 seed em SEV-1, mal diagnosticado. Entre +0,5 e +1,0 não foi medido |
| Prior shift (S3) | Logit +0,25 (m = 0,5): SEV-1 em 5/5 e SEV-2 em 3/5 | — |
| Bug de unidade (S4) | Em 15% das linhas (m = 0,5), D6 em todos os lotes alertados, só em SEV-1. A regra P02 age no D6 em qualquer severidade, então a quarentena acontece | Em 7,5% das linhas, o bug passa (1 seed em SEV-1, mal diagnosticado) |
| Bug de unidade a 45% | Em um seed, o contrato bloqueou um lote inteiro (regra H10) | — |

### Limites do próprio estudo

- **Intervalo otimista:** o intervalo de Wilson trata os lotes como independentes. Lotes do mesmo seed não são, então o intervalo real é mais largo.
- **Circularidade só atenuada:** 5 seeds por célula, e os mecanismos continuam os desenhados para o projeto. O estudo mostra estabilidade dentro desses mecanismos, não acerto em mecanismos novos.
