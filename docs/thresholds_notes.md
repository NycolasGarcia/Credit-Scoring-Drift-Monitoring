## Leitura

- **A convenção de mercado é conservadora para estes lotes.** Num lote de 6.000 propostas sem drift, o maior PSI de feature foi 0,005 e o do score 0,005, cerca de 20× abaixo do corte de 0,10. A regra de calibração mantém a convenção como piso: um corte menor detectaria o choque econômico (S1) mais cedo, mas também alertaria para mudanças pequenas que não afetam a decisão. Drift não é degradação (§8.1).
- **A queda de AUC é o único sinal com ruído relevante.** A AUC de 6.000 propostas oscila: o corte proposto de 0,02 dava 1,2% de falso alarme. Pela regra de Bonferroni, sobe para 0,025.
- **O bad rate observado no holdout fica ~2% acima do esperado** (mediana nula de 1,02). É a calibração do champion na população de 2013, bem abaixo do corte de 1,2.
- **O descolamento por segmento tem ruído alto** (mediana 0,28 em logit). Por isso ele não gera alerta sozinho: só decide entre D3 e D2 quando o bad rate já alertou. O corte de 0,5 deixa 0,2% de falso diagnóstico no controle.
- **A meta de falso alarme (5% SEV-1, 0% SEV-2) continua PROPOSTO:** é decisão do autor (§15). Com os cortes calibrados, o controle fica em 0,2% e 0%.
