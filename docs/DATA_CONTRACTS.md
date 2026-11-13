# Contratos de dados

> Gerado por `make contracts-doc` (`src/contracts/catalog.py`) a partir de `src/contracts/rules.py`,
> `config/contracts/contract.yaml` e `src/simulation/bad_batch.py`. Não editar à mão.
> Decisões de desenho: [ADR-0008](adr/0008-data-contracts.md).

O contrato de **entrada** valida cada lote de propostas antes da pontuação; o de **saída**
valida o lote pontuado. Biblioteca: Pandera 0.36 (`pandera.pandas`), validação `lazy`
(todas as falhas coletadas), `strict=True` (coluna fora do contrato bloqueia), sem coerção
de tipo.

**Política do gate (GR-1, GR-2):**

- escopo `schema` ou `batch` com falha → **lote bloqueado**: 0 linhas pontuadas, exit code 2,
  alerta `CONTRACT_BATCH_BLOCKED`, lote inteiro em `data/quarantine/<batch_id>/`;
- escopo `row` com falha → **linhas em quarentena**, restante pontuado; se a fração de linhas
  reprovadas passar de 1% → lote bloqueado (fonte suspeita);
- regras `soft` → só aviso no relatório e no log;
- relatório de violação **só com agregados** (regra, escopo, contagem, taxas, nomes de
  categorias novas) — nenhum valor de linha (GR-10).

## Regras

| Regra | Severidade | Escopo | O que garante | Defeito que a dispara isoladamente |
|---|---|---|---|---|
| H01 | hard | schema | colunas exatamente as do contrato (sem extra, sem faltante) | `extra_column`, `missing_column` |
| H02 | hard | schema | tipo de cada coluna conforme o contrato | `wrong_type` |
| H03 | hard | schema | loan_key único no lote | `duplicate_keys` |
| H04 | hard | row | campos críticos não nulos | `null_critical` |
| H05 | hard | row | valores dentro de faixas possíveis | `negative_income` |
| H06 | hard | row | valores categóricos e prazo dentro do domínio | `unknown_grade` |
| H07 | hard | row | data de emissão dentro da janela válida (sem data futura) | `future_date` |
| H08 | hard | row | parcela coerente com valor, taxa e prazo | `incoherent_installment` |
| H09 | hard | row | sem valores sentinela (placeholder de bureau) | `sentinel` |
| H10 | hard | batch | escala da renda do lote compatível com a referência | `monthly_income` |
| H11 | hard | row | contagens e saldos não negativos | `negative_count` |
| S01 | soft | batch | taxa de nulos por coluna não sobe além da tolerância | teste direto em `tests/test_contracts.py` |
| S02 | soft | batch | sem categorias inexistentes na referência | `new_category` |
| S03 | soft | batch | volume do lote dentro da banda | teste direto em `tests/test_contracts.py` |
| S04 | soft | batch | cauda extrema de utilização dentro do esperado | teste direto em `tests/test_contracts.py` |
| O01 | hard | schema | lote pontuado: colunas, tipos e loan_key único | teste direto em `tests/test_contracts.py` |
| O02 | hard | row | score em [0, 1] e decisão no domínio, sem nulos | teste direto em `tests/test_contracts.py` |
| O03 | hard | batch | decisão consistente com score e limiar | teste direto em `tests/test_contracts.py` |

## Parâmetros (contrato v1)

- `loan_amnt`: [500, 40000]
- `int_rate`: [0.01, 40]
- `installment`: [0.01, 5000]
- `annual_inc`: [1, 1e+07]
- `dti`: [0, 100]
- `fico_range_low`: [300, 850]
- `emp_length`: [0, 10]
- `credit_history_months`: [0, 1200]
- domínio `term`: [36, 60]
- domínio `grade`: ['A', 'B', 'C', 'D', 'E', 'F', 'G']
- sentinela `tot_hi_cred_lim`: [9999999.0]
- coerência da parcela: erro relativo ≤ 5%
- escala da renda do lote: mediana / referência ∈ [0.5, 2]
- janela de emissão: 2007-06-01 a 2019-03-01
- campos obrigatórios: loan_key, issue_d, loan_amnt, term, int_rate, installment, grade, annual_inc, dti, fico_range_low, home_ownership, verification_status, purpose
- não negativos: delinq_2yrs, inq_last_6mths, mths_since_last_delinq, open_acc, pub_rec, revol_bal, revol_util, total_acc, mort_acc, pub_rec_bankruptcies, acc_open_past_24mths, bc_util, avg_cur_bal, tot_hi_cred_lim, num_actv_rev_tl, percent_bc_gt_75, mths_since_recent_inq, mo_sin_old_rev_tl_op, tot_cur_bal, total_bc_limit

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
