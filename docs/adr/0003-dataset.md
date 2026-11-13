# ADR-0003 — Escolha do dataset: Lending Club (empréstimos aceitos 2007–2018)

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F1

## Contexto

O projeto exige dataset tabular financeiro com alvo binário e pelo menos 5.000 amostras. Além disso, o objetivo central (monitorar e responder à degradação) se beneficia muito de um **eixo temporal real**: ele permite mostrar drift natural, rótulo atrasado e concept drift com dado de verdade, não só simulado.

Fatos verificados (fonte: EDA `notebooks/01_eda.ipynb` sobre o arquivo bruto de sha256 `3eae03c2…f36a`):

- `accepted_2007_to_2018Q4.csv`: 2.260.668 empréstimos válidos (mais 33 linhas de rodapé), 151 colunas, safras de jun/2007 a dez/2018.
- Licença no Kaggle: **CC0: Public Domain** (metadados da API do Kaggle).
- Snapshot do dado ≈ mar/2019 (`last_pymnt_d` máximo).
- O German Credit (UCI 144) tem 1.000 instâncias, abaixo do mínimo do enunciado.

## Decisão

Usar o **Lending Club, arquivo de empréstimos aceitos**, restrito a aplicações **individuais** (`application_type = Individual`). Aplicações conjuntas só existem a partir de dez/2015 e exigiriam features de co-tomador ausentes na referência.

O arquivo de recusados (`rejected_2007_to_2018Q4`) **não** entra no modelo. Ele serve apenas para documentar o viés de seleção (reject inference).

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Home Credit Default Risk | Atributos fortes para viés (gênero, idade) | Sem eixo temporal absoluto; drift seria 100% simulado; download exige aceitar regras de competição (não verificado) | O eixo temporal real vale mais para a tese do projeto |
| German Credit | Clássico, atributos de viés | 1.000 amostras (< 5.000 exigidas) | Viola o requisito RO-17 |
| Dados sintéticos | Controle total | Nenhum drift real; pouca credibilidade | Não demonstra o problema real |

## Consequências

**Boas:**
- Drift natural real entre safras (PSI > 0,25 em 5 features em 2018 contra 2013, segundo a EDA).
- O rótulo atrasado é real: as safras 2017–2018 são majoritariamente `Current`.
- Volume abundante para referência, holdout e lotes mensais de produção.
- Licença CC0 permite publicar estatísticas agregadas.

**Ruins / custos aceitos:**
- Atributos para análise de viés são fracos: não há gênero nem idade, só região (`addr_state`), `emp_length` e `home_ownership`. A análise de fairness (F8) terá esse limite declarado.
- O dataset contém só aprovados (viés de seleção). Documentado no data card e no model card.
- O dicionário de dados disponível é uma cópia de terceiros (Figshare). A classificação de vazamento foi confirmada empiricamente (ADR-0004).

## Como saberemos que a decisão estava errada

Se a análise de fairness da F8 não conseguir produzir nenhuma métrica significativa com os atributos disponíveis, ou se o drift natural (S5) for indistinguível de ruído. Nesses casos, reavaliar o Home Credit como dataset complementar só para a análise de viés.
