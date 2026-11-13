# Data Card — Lending Club (empréstimos aceitos)

> Fonte dos números: EDA `notebooks/01_eda.ipynb` e `docs/evidence/data/split_manifest.json`, ambos sobre o arquivo bruto de sha256 `3eae03c28fd9d2e8a076ebeb73507e8d4d0f44d90500decdb0936e0933d1f36a`.

## Origem e licença

| Item | Valor |
|---|---|
| Dataset | "All Lending Club loan data" (Kaggle `wordsforthewise/lending-club`) |
| Arquivo usado | `accepted_2007_to_2018Q4.csv` |
| Licença | CC0: Public Domain |
| Obtenção | Download manual pelo autor; caminho via `CDM_RAW_DATA_PATH` |
| Dicionário | `LCDataDictionary.xlsx` (cópia pública no Figshare, artigo 20016077) |
| Snapshot | ≈ 2019-03 (último mês de pagamento observado) |

## Volume e escopo

- 2.260.668 empréstimos, 151 colunas, safras de jun/2007 a dez/2018.
- Escopo do modelo: aplicações **individuais** (2.139.958). Aplicações conjuntas (120.710) só existem a partir de 2015-12 e estão fora do escopo.

| Safra | Individuais | % Current | Bad rate (resolvidos) | Bad rate (maduros) |
|---|---|---|---|---|
| 2012 | 53.367 | 0,0 | 16,2% | 16,2% |
| 2013 | 134.814 | 0,0 | 15,6% | 15,6% |
| 2014 | 235.629 | 5,1 | 18,5% | 14,6% |
| 2015 | 420.584 | 10,3 | 20,2% | 14,9% |
| 2016 | 425.618 | 30,9 | 23,3% | 16,1% |
| 2017 | 401.154 | 59,0 | 22,8% | — |
| 2018 | 426.257 | 86,3 | 15,2% | — |

(% Current calculado sobre todas as aplicações da safra; demais colunas sobre individuais.)

## Alvo

Inadimplência = `Charged Off` ou `Default`; adimplente = `Fully Paid`. Empréstimos em andamento ficam sem rótulo. Treino e avaliação com rótulo usam apenas empréstimos **maduros** (prazo integral decorrido até o snapshot). Detalhes no [ADR-0004](adr/0004-target-maturity-leakage.md).

## Partições

Ver [ADR-0005](adr/0005-reference-production-split.md). Referência = safra 2013 (80%); holdout = safra 2013 (20%); produção natural = 2014–2018.

## Features

32 colunas de originação mais `credit_history_months` (derivada de `earliest_cr_line`). A classificação completa das 151 colunas está em [data_inventory.md](data_inventory.md).

## Limitações conhecidas

1. **Viés de seleção (reject inference).** O arquivo contém só empréstimos **aprovados** pela política do Lending Club. O modelo não sabe como se comportariam os recusados, e o risco estimado vale para a população já filtrada.
2. **Censura do rótulo.** Nas safras ≥ 2016, o bad rate entre resolvidos superestima o risco (até +7 pp em 2016). Safras ≥ 2017 não têm empréstimo maduro no snapshot.
3. **Nulos estruturais.** Features de bureau inexistem antes de 2012, por isso a referência começa em 2013. `mths_since_last_delinq` (~57% nulo) e `mths_since_recent_inq` (~11%) têm nulo informativo: o evento nunca ocorreu.
4. **Mudança de política ao longo do tempo.** `verification_status` tem PSI de 0,47 em 2018 contra 2013, o que reflete processo interno do credor e não o perfil do tomador. `int_rate` e `grade` são saídas do modelo de precificação do próprio Lending Club.
5. **Categorias novas na produção.** `home_ownership` ∈ {ANY, NONE} e `purpose = educational` não existem na referência.
6. **Atributos de viés limitados.** Não há gênero nem idade. Os segmentos possíveis são `addr_state`, `emp_length` e `home_ownership`.
7. **Dicionário de terceiros.** A cópia do dicionário não é a página oficial do credor. A classificação de vazamento foi confirmada por AUC univariado.

## Privacidade

Nenhum dado pessoal sensível (LGPD art. 5º, II). Identificadores diretos são removidos (`member_id`, `url`) ou pseudonimizados (`id` → `loan_key`, HMAC). Texto livre (`emp_title`, `desc`, `title`) e `zip_code` nunca são carregados. O plano completo fica para a F8.
