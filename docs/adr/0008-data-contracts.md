# ADR-0008 — Contratos de dados, gate em dois níveis e política de quarentena

- **Status:** aceito
- **Data:** 2026-11-13
- **Fase:** F3

## Contexto

Todo lote mensal de propostas precisa ser validado antes da pontuação: lixo não pode virar decisão de crédito, e quando tentar entrar o motivo precisa ficar registrado. Verificações feitas antes do desenho:

- **Pandera 0.36.0 (NV-12, verificado na versão fixada):**
  - import recomendado `pandera.pandas`;
  - `strict=True` rejeita coluna extra (`column_in_schema`), e coluna ausente gera `column_in_dataframe`;
  - `unique=[...]` acusa duplicatas com o índice da linha;
  - `lazy=True` coleta todas as falhas;
  - os casos de falha trazem o **valor bruto** (`failure_case`), o que é risco de vazamento em relatório;
  - um check de DataFrame que devolve Series é reportado **uma vez por coluna** de cada linha reprovada.
- **Lotes reais** (holdout + 60 meses de produção) trazem defeitos esparsos por linha: parcela incoerente em até 0,07% das linhas, sentinela `tot_hi_cred_lim = 9.999.999` em 13 meses, uma renda de US$ 110 mi e DTI negativo. Bloquear o lote inteiro por qualquer linha ruim barraria quase todos os meses reais.

## Decisão

1. **Pandera** como biblioteca de contrato, com dois schemas: **entrada** (lote de propostas) e **saída** (lote pontuado). Validação `lazy`, `strict=True`, sem coerção de tipo.
2. **Contrato declarativo:** limites, domínios, tolerâncias e janelas em `config/contracts/contract.yaml`; regras com id, severidade e escopo em `src/contracts/rules.py`. Cada `Check` leva o id da regra como nome, e toda falha é rastreável ao catálogo. O catálogo publicado (`docs/DATA_CONTRACTS.md`) é **gerado** dessas fontes.
3. **Gate em dois níveis** (refina o GR-1):
   - regra hard de escopo **schema** (colunas, tipos, unicidade) ou **batch** (escala da renda do lote) → **lote bloqueado**: 0 linhas pontuadas, exit code 2, alerta `CONTRACT_BATCH_BLOCKED`;
   - regra hard de escopo **row** → **linhas em quarentena** e o restante é pontuado. Se a fração de linhas reprovadas passar de **1% (PROPOSTO)**, o lote inteiro é bloqueado (fonte suspeita);
   - regras **soft** (nulos acima da referência, categoria nova, volume, cauda extrema) → só aviso.
4. **Quarentena (GR-2):** `data/quarantine/<batch_id>/` com as linhas retidas (chave pseudonimizada) e `report.json`. O relatório tem **só agregados**: regra, escopo, contagem por linhas distintas, taxas e nomes de categorias novas. Nenhum valor de linha (GR-10), e um teste garante isso.
5. **O contrato de saída** valida score em [0, 1], decisão no domínio e consistência entre decisão, score e limiar. Se falhar, o lote pontuado é descartado.
6. **A regra de idade ≥ 18 anos não se aplica:** o dataset não tem idade.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Great Expectations | Data Docs prontos, ecossistema grande | Configuração pesada (contexto, suites, checkpoints), mais difícil de testar como código; sem ganho para lotes batch locais | Pandera é Python puro, testável e já usado no TC3 |
| Bloquear o lote por qualquer falha (GR-1 literal) | Simples | Barraria quase todos os meses reais por defeitos esparsos; alarme constante vira ruído | Fadiga de alerta |
| Só quarentena de linhas, nunca bloquear | Máximo aproveitamento | Não detecta fonte quebrada nem bug estrutural | Falha estrutural precisa parar o pipeline |
| Coerção de tipos (`coerce=True`) | Tolera pequenas variações | Esconde bug de fonte (texto virando número silenciosamente) | Tipo errado é sinal, não ruído |

## Consequências

**Boas:**
- Meses reais passam com poucas linhas retidas: 61/61 lotes reais sem bloqueio, fração máxima de 0,049%.
- Lotes estruturalmente ruins são barrados. Cada uma das 11 regras hard tem um defeito que a dispara isoladamente (`tests/test_contracts.py`).
- O catálogo documentado não diverge do aplicado.

**Ruins / custos aceitos:**
- A tolerância de 1% é PROPOSTO, e um lote com até 1% de linhas ruins passa parcialmente.
- **O contrato só pega o bug de unidade (D6) quando ele é grosseiro:** a regra de escala usa a mediana. Bugs parciais ficam para a detecção de drift (`docs/DATA_CONTRACTS.md`, seção D6).
- A checagem de coerência da parcela depende de três colunas; se uma vier com tipo errado, a regra também acusa, como falha colateral documentada.

## Como saberemos que a decisão estava errada

- Meses reais passarem a ser bloqueados com frequência (falso alarme do contrato).
- Um defeito injetado passar pelo gate e chegar à pontuação.
- Um relatório de quarentena conter valor de linha.
