# Changelog

Mudanças relevantes por fase, da mais recente para a mais antiga. Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). O detalhe de cada fase (portões, evidências, veredito) está em [docs/PROGRESS.md](docs/PROGRESS.md); as decisões, em [docs/adr/](docs/adr/).

## [Não publicado]

Nada ainda.

## F3 — Contratos de dados e quality gate (2026-11-13)

### Adicionado
- Contrato de entrada (Pandera, `strict` + `lazy`) com 11 regras rígidas (H01–H11) e 4 de aviso (S01–S04); contrato de saída com 3 regras (O01–O03). Parâmetros em `config/contracts/contract.yaml`.
- Quality gate em dois níveis ([ADR-0008](docs/adr/0008-data-contracts.md)): falha estrutural ou > 1% de linhas inválidas bloqueia o lote (exit 2, alerta `CONTRACT_BATCH_BLOCKED`, 0 linhas pontuadas); linhas inválidas isoladas vão para `data/quarantine/<batch_id>/`.
- Relatório de violação só com agregados (sem valores de linha).
- Gerador de lote ruim com 13 defeitos catalogados, cada um ligado à regra que deve dispará-lo.
- Comandos `make validate`, `make validate-bad`, `make contracts-d6` e `make contracts-doc`.
- `docs/DATA_CONTRACTS.md` gerado do código, com teste de sincronia; apêndice sobre o bug de unidade (renda mensal × anual).
- Evidências em `docs/evidence/contracts/`.

### Achados
- Os 61 lotes reais (holdout + 60 meses de produção) passam sem bloqueio; quarentena máxima de 0,049% das linhas.
- Sentinela `9.999.999` em `tot_hi_cred_lim` encontrada em 13 meses.
- Bug de unidade: o contrato bloqueia a partir de 50% das linhas afetadas; abaixo disso, o PSI de `annual_inc` sinaliza a partir de ~20%.

## F2 — Modelo, calibração e perfil de referência (2026-11-12 a 2026-11-13)

### Adicionado
- Tracking MLflow (SQLite) e Registry com alias `champion`.
- Dummy, regressão logística e XGBoost com CV estratificada e validação fora do tempo (2014, 2015); calibração Platt/isotônica escolhida por Brier.
- Métricas de crédito: AUC, Gini, KS, PR-AUC, Brier, bad rate esperado × observado.
- PSI com bins fixados pela referência e `reference_profile.json` versionado com o modelo.
- RUN records e `docs/EXPERIMENTS.md` gerados por código.
- Economia realizada a partir do caixa do credor e validação FP/FN do limiar (`make cost`).
- Notebook `02_modelagem.ipynb` e rascunho do model card.

### Alterado
- Limiar de aprovação: premissas de custo medidas no caixa realizado + funding declarado de 5% a.a. Champion v2 com limiar 0,495 ([ADR-0016](docs/adr/0016-empirical-cost-threshold.md), supersede o [ADR-0007](docs/adr/0007-cost-threshold.md)).
- Portão de calibração reformulado para |bad rate esperado − observado| ≤ 1 pp, por decisão do autor.

### Corrigido
- RUN records eram marcados como de árvore suja após a escrita do índice; o estado do git passou a ser capturado no início do job.

## F1 — Dados, alvo e separação referência × produção (2026-11-12)

### Adicionado
- Inventário das 151 colunas em YAML como fonte única de allowlist e de PII; `docs/data_inventory.md` gerado.
- Loader tipado, alvo binário com maturação por prazo, allowlist de features de originação, pseudonimização HMAC.
- Partições referência (2013), holdout (2013) e produção (2014–2018) com manifesto e hashes.
- Notebook `01_eda.ipynb`, data card e ADRs 0003, 0004 e 0005.

### Corrigido
- Caminhos relativos resolvidos a partir da raiz do projeto.

## F0 — Fundação e travas de publicação (2026-11-12)

### Adicionado
- Estrutura do repositório, `pyproject.toml` com uv e versões exatas, lock file.
- ruff, pre-commit, Makefile, configuração via pydantic-settings e logging JSON com filtro de privacidade.
- Verificação de publicação (`make publish-check`), hook de mensagem de commit e CI (lint, testes, publicação).
- Esqueleto de documentação, templates e ADRs 0001 e 0002.
