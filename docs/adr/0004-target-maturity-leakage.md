# ADR-0004 — Alvo, maturação do rótulo e exclusão de vazamento

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F1

## Contexto

`loan_status` mistura empréstimos encerrados e em andamento. Um empréstimo de 36 meses só tem desfecho confiável depois que o prazo termina. Antes disso, quem já "resolveu" é desproporcionalmente quem inadimpliu cedo. O arquivo também traz dezenas de colunas preenchidas **depois** da concessão, que vazam o desfecho.

Evidências (EDA `notebooks/01_eda.ipynb`, raw sha256 `3eae03c2…f36a`):

- Bad rate por safra, comparando **resolvidos** com **maduros**: 2014 = 18,5% × 14,6%; 2015 = 20,2% × 14,9%; 2016 = 23,3% × 16,1%. Usar só "resolvidos" superestima o risco das safras jovens.
- Proporção `Current` por safra, em aplicações individuais: 5% (2014), 10% (2015), 31% (2016), 58% (2017), 86% (2018). *Errata 2026-11-12: a primeira versão citava 59% em 2017, calculado sobre todas as aplicações; a decisão não muda.*
- AUC univariado de colunas pós-originação em empréstimos maduros de 2013: `recoveries` 0,958; `last_fico_range_*` 0,896; `last_credit_pull_d` 0,856; `total_rec_prncp` 0,845. Nenhuma feature de originação passa de 0,67.

## Decisão

1. **Alvo** (`src/data/target.py`):
   - `Charged Off`, `Default` e "Does not meet the credit policy. Status:Charged Off" → **1**;
   - `Fully Paid` e "Does not meet the credit policy. Status:Fully Paid" → **0**;
   - `Current`, `In Grace Period` e `Late (*)` → **sem rótulo** (NaN);
   - status desconhecido → **erro**: status novo só entra por decisão.
2. **Maturação:** `is_mature = issue_d + term ≤ snapshot`. Treino, calibração e avaliação com rótulo (L4) usam **apenas empréstimos maduros e resolvidos** (base do guardrail GR-8).
3. **Allowlist, não denylist:** cada uma das 151 colunas está classificada em `config/data/column_inventory.yaml`. Só entra no modelo o que tem `use: feature` **e** `cat: originacao`, o que hoje dá 32 colunas brutas mais 1 derivada (`credit_history_months`). As fontes da classificação são a aba `browseNotes` do dicionário (campos visíveis na listagem) e o scan de AUC acima.
4. **O loader nem lê** colunas pós-originação nem texto livre. A única exceção é `last_pymnt_d`, lida só para datar o snapshot e descartada em seguida.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Rotular por "resolvido" (sem maturação) | Mais dados nas safras recentes | Viés de sobrevivência comprovado (+4 a +7 pp no bad rate) | Distorce calibração e L4 |
| Tratar `Late (31-120)` como mau | Rótulo antecipado | Parte cura; mistura definições | Fica como *proxy* de rótulo para a F7 (§8.5), não como alvo |
| Denylist de colunas vazadas | Simples | Coluna nova entra por omissão | Contraria o princípio de entrada por decisão |
| Janela de desempenho fixa (ex.: 12 meses) | Rótulo mais cedo | Exige histórico de pagamentos mês a mês, que o arquivo não tem | Inviável com este dado |

## Consequências

**Boas:** rótulo sem viés de sobrevivência; vazamento bloqueado por construção e por teste (`tests/test_inventory_features.py`); o *label lag* da produção natural é real e mensurável.

**Ruins / custos aceitos:** safras ≥ 2017 não têm nenhum empréstimo maduro no snapshot. O desempenho com rótulo na produção natural só existe para 2014–2016, e de forma parcial nos 60 meses.

## Como saberemos que a decisão estava errada

- AUC de treino acima de 0,90 (portão da F2), que indicaria vazamento remanescente.
- Diferença grande entre o bad rate esperado (calibrado) e o observado na referência madura.
- Status novo em `loan_status`, que dispara o erro do `map_target`.
