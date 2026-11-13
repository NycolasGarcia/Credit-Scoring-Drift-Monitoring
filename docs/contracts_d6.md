## Caso D6: o contrato pega o bug de unidade, ou só o drift pega?

**Cenário:** a fonte passa a enviar `annual_inc` **mensal** em vez de anual (× 1/12). Cada valor continua plausível isoladamente, porque uma renda mensal de US$ 5 mil passa por qualquer faixa de linha. Por isso nenhuma regra por linha consegue detectá-lo. A regra **H10** compara a **mediana do lote** com a mediana da referência (US$ 63.981) e bloqueia fora de [0,5; 2,0]×.

Varredura reprodutível (`make contracts-d6`; holdout com 26.961 propostas, seed 7; evidência em [`evidence/contracts/d6_sweep.json`](evidence/contracts/d6_sweep.json)):

| Fração das linhas com renda mensal | Mediana / referência | Contrato | PSI de `annual_inc` |
|---|---|---|---|
| 10% | 0,938 | passa | 0,069 |
| 20% | 0,857 | passa | 0,232 |
| 30% | 0,766 | passa | 0,457 |
| 40% | 0,625 | passa | 0,748 |
| 50% | 0,313 | **bloqueia (H10)** | 1,095 |
| 60% | 0,133 | **bloqueia (H10)** | 1,524 |
| 100% | 0,083 | **bloqueia (H10)** | 8,078 |

**Leitura:**

1. **O contrato pega o bug grosseiro**, em que a fonte inteira ou a maioria dela mudou de unidade, e o barra antes da pontuação (D0/D6 → quarentena, nunca retreino).
2. **O bug parcial passa pelo contrato** por construção: a mediana é robusta, e é isso que evita falso alarme do contrato em meses reais. Quem o vê é a camada **L2** (drift por feature): o PSI de `annual_inc` passa de ~0,23 a partir de 20% das linhas afetadas.
3. **As camadas são complementares.** O contrato responde "o dado é válido?"; o drift responde "a população mudou?". Um salto abrupto, num único lote, concentrado numa variável e com fator ~constante é a assinatura de D6. A heurística que separa D6 de choque econômico real (D1) é avaliada na F5 (caixa 5.8) sobre o cenário S4.

**Consequência operacional:** o playbook do alerta de drift em `annual_inc` deve **perguntar à fonte antes de qualquer resposta de modelo** (§8.7, ramo "mudança abrupta, 1 lote, fator constante").
