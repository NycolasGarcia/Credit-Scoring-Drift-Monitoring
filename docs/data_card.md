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
| 2016 | 425.618 | 30,7 | 23,3% | 16,1% |
| 2017 | 401.154 | 58,3 | 22,8% | — |
| 2018 | 426.257 | 86,2 | 15,2% | — |

Todas as colunas são calculadas sobre aplicações individuais (escopo do modelo).

Cardinalidade das categóricas: `grade` 7 níveis em todas as safras; `verification_status` 3 (exceto 2007); `purpose` 13–14; `home_ownership` 3–5; `addr_state` cresce de 38 (2007) para 50 (2016+).

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

## Qualidade e estatística (EDA, seções 8–14)

- **Sem duplicatas e sem valores impossíveis** no dado real: renda ≤ 0, DTI < 0, juros fora de (0, 40], valor fora de [500, 40k], FICO fora de [300, 850] e histórico de crédito negativo têm contagem praticamente nula.
- **Utilização acima de 100%** é real (cartão estourado): `revol_util` > 100 em 7.005 empréstimos e `bc_util` > 100 em 29.494 (2007–2018).
- **Parcela incoerente** com a amortização de `loan_amnt`, `int_rate` e `term` (> 2%): 2.590 casos, concentrados em 2008–2011. O erro mediano é zero.
- **Valor sentinela:** `tot_hi_cred_lim` = 9.999.999 em 14 empréstimos (2013–2018), com cara de placeholder do bureau.
- **Assimetria forte** nas monetárias (`annual_inc` skew ≈ 19, `revol_bal` ≈ 28) e nas contagens raras. A regra IQR é inadequada para contagens, em que Q1 = Q3 = 0.
- **Poder preditivo univariado** baixo, exceto `int_rate` (IV 0,38) e `grade` (IV 0,36). Nenhuma |ρ| com o alvo passa de 0,22.
- **Redundâncias** (Spearman > 0,9): `tot_hi_cred_lim` × `tot_cur_bal`, `loan_amnt` × `installment`, `avg_cur_bal` × `tot_cur_bal`, `pub_rec` × `pub_rec_bankruptcies`.

## Economia realizada (EDA seção 15; RUN-20261113-calib-COST-01)

Lida das colunas `use: custo`, só em agregado, na referência 2013 madura:

- Perda líquida de um mau, ponderada por valor: **0,327** do principal (perda média por grade entre 0,31 e 0,36).
- Um bom realiza **0,757** dos juros contratuais, ponderado por valor (pré-pagamento).
- **16%** dos maus pagadores têm caixa líquido positivo (default tardio).

Implicação para o limiar: [ADR-0016](adr/0016-empirical-cost-threshold.md).

## Privacidade

Nenhum dado pessoal sensível (LGPD art. 5º, II). Identificadores diretos são removidos (`member_id`, `url`) ou pseudonimizados (`id` → `loan_key`, HMAC). Texto livre (`emp_title`, `desc`, `title`) e `zip_code` nunca são carregados. O plano completo fica para a F8.
