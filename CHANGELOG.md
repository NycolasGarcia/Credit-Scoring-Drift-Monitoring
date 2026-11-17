# Changelog

Mudanças relevantes por fase, da mais recente para a mais antiga. Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). O detalhe de cada fase (portões, evidências, veredito) está em [docs/PROGRESS.md](docs/PROGRESS.md); as decisões, em [docs/adr/](docs/adr/).

## [Não publicado]

### Adicionado
- Estudo de robustez (`make robustness` → `docs/ROBUSTNESS.md`, RUN-20261117-calib-ROBUST-01): cada cenário repetido com 5 seeds novos e 4 magnitudes (0,25 a 1,5 vezes a oficial), pelo mesmo caminho da produção (simulador, contrato, score, detector), com a comparação de respostas por seed na magnitude oficial. Regra de leitura declarada em `config/monitoring/robustness.yaml` antes da execução.

### Achados
- Nenhum falso alarme no controle nem antes do início do drift; detecção de 5/5 na magnitude oficial nos quatro cenários.
- O S2 falha a regra de diagnóstico declarada (19 de 20 lotes; limite inferior de 76% contra 80%): num seed, o primeiro alerta, em SEV-1 na rampa, foi lido como D2.
- Os valores do seed oficial ficaram no lado favorável: o modo conservador rende mediana de +US$ 2,19 mi no S2 (oficial 2,94) e a recalibração, +US$ 0,27 mi no S3 (oficial 0,87). O sinal de toda resposta se mantém em todos os seeds.
- Limites de sensibilidade: concept drift com logit +0,5 e bug de unidade em 7,5% das linhas passam sem detecção.

## F7 — Resposta à degradação: guardrails, playbooks e retreino controlado (2026-11-17)

### Adicionado
- Etapa `respond` do job com a matriz de resposta declarativa (`config/response/policy.yaml`): diagnóstico e severidade → ações automáticas e humanas, circuit breaker com histerese, cadeia de guardrails (kill switch, quarentena, modo conservador, limiar) com código de motivo por decisão, modo `dry_run` e controles relidos a cada lote, sem deploy.
- Modo conservador por valor esperado com o risco corrigido pela última razão observado/esperado ([ADR-0019](docs/adr/0019-conservative-mode-by-value.md)) e fila de revisão limitada a 15% do lote, com o excedente recusado pelo motivo R11 ([ADR-0021](docs/adr/0021-review-queue-capacity.md)).
- Ciclo de vida do modelo: recalibração e challenger em janela recente, só com dado aprovado no contrato e rótulo maduro (GR-7, GR-8), gate de promoção (GR-5), promoção e rollback por aliases (GR-6); [ADR-0012](docs/adr/0012-guardrails-conservative-mode.md) e [ADR-0013](docs/adr/0013-retraining-gate-rollback.md).
- Comparação de respostas por cenário com o valor realizado (`make respond-compare` → `docs/RESPONSE_EVALUATION.md`), avaliação em sombra e ensaio de promoção/rollback no registry de ensaio (`make respond-drill`).
- Game day na visão do operador (`make gameday-watch`, `make gameday`, `make gameday-shadow`) e o primeiro postmortem, [INC-0001](docs/incidents/0001-s2-concept-drift-dti.md).
- Métricas e painéis de resposta no Grafana (modo conservador, correção de risco, decisões por tipo, regra da política).

### Alterado
- O teto de 14% de bad rate deixou de ser o corte do modo conservador (ADR-0019); passou a ser só métrica de acompanhamento.
- O critério de calibração do gate passou a ser relativo ao champion ([ADR-0020](docs/adr/0020-relative-calibration-gate.md)).
- A6 (challenger em sombra) passou a ser ação humana, com comando no playbook ([ADR-0022](docs/adr/0022-challenger-shadow-human.md)).
- RUNBOOK: triagem com o ramo de rótulo maduro separando D2 de D3 pela concentração em segmento, seção de resposta (comandos, controles, códigos de motivo), playbooks com a ação automática de cada alerta, promoção/rollback e procedimento de game day.

### Corrigido
- A leitura da comparação de respostas dizia que o gate reprovava o challenger do S2, o que deixou de valer com o ADR-0020.

### Achados
- O modo conservador por valor rende +US$ 2,94 mi no S2 e +US$ 2,66 mi no S3; forçado sobre o bug do S4, custaria US$ 6,3 mi (RUN-20261117-response-ALL-01).
- No game day, o concept drift no DTI alto não derrubou a AUC: a separação entre D2 e D3 precisa olhar o segmento.

## F6 — Observabilidade: logs, métricas, dashboard e alertas (2026-11-15)

### Adicionado
- Job de monitoramento por lote (`src/pipeline.py`): ingest → validate → score → detect → evaluate → alert → respond → record, com evento JSON por etapa e log por execução sem PII.
- Métricas no Pushgateway (22 gauges catalogados em `docs/METRICS.md`), MLflow `monitoring` com run pai por execução e run filho por lote, relatório Evidently anexado.
- Stack local via Compose (Prometheus, Pushgateway, Grafana, renderer), dashboard como código com 13 painéis e prints gerados pela API de render (`make screenshots`).
- Catálogo de alertas (`config/monitoring/alerts.yaml`) com regras do Prometheus e testes do `promtool` gerados, dead man's switch e playbook por alerta no `docs/RUNBOOK.md`; `make check-rules` também no CI.
- `make monitor`, `make replay`, `make alerts`, `make check-rules`, `make screenshots`, `make stack-status`; [ADR-0010](docs/adr/0010-observability-stack.md) e [ADR-0011](docs/adr/0011-severity-alert-policy.md).
- Varredura do corte SEV-2 da razão observado/esperado (`make sweep-l4`): regra de escolha declarada em `config/monitoring/l4_sweep.yaml` antes da execução, distribuição nula com seed nova e validação em variantes de S2/S3 que não participam da escolha.

### Alterado
- SEV-2 da razão observado/esperado: 1,5 → 1,25 ([ADR-0018](docs/adr/0018-l4-sev2-cut.md), RUN-20261115-calib-L4CUT-01). S2 e S3 passam a chegar a SEV-2 no primeiro alerta; detecção dos seis cenários refeita (RUN-20261115-monitor-S0-01 … S5-01).
- Dead man's switch global, não por cenário: o monitor é um só.

### Corrigido
- Runs por lote do MLflow iam para o experimento `training` ao carregar o champion depois de abrir o run pai; agora ficam em `monitoring` (teste de regressão).
- Leitura da F5: no S2, D3 cobre 4 de 4 lotes alertados, não 5.

### Achados
- Os seis cenários disparam os alertas esperados; o S0 não dispara nenhum. O dead man's switch dispara nas transições entre replays (monitor de fato parado por mais de 30 s).

## F5 — Detecção de drift e avaliação do detector (2026-11-13)

### Adicionado
- Detector por lote em três camadas: L2 (PSI com bins fixos da referência, KS, χ², Wasserstein), L3 (PSI do score, aprovação), L4 (desempenho dos rótulos que amadurecem no lote, com descolamento por segmento).
- Motor de severidade com direção por sinal e diagnóstico pela árvore §8.7, incluindo assinatura de bug de unidade (D6) e separação D3 × D2 por segmento.
- Calibração dos limiares por bootstrap A/A no controle (`make calibrate`): 6 limiares CALIBRADO; falso alarme composto 0,2% (SEV-1+) e 0% (SEV-2+).
- Relatório Evidently por cenário com teste `psi_ref` registrado (PSI com bins da referência) e cruzamento exato com o PSI próprio (`make detect`).
- Avaliação do detector contra os manifestos (§8.8) e documentos gerados `THRESHOLDS.md` e `DRIFT_EVALUATION.md` (`make drift-docs`).
- [ADR-0009](docs/adr/0009-drift-detection-methodology.md); NV-8, NV-9 e NV-10 fechados.

### Alterado
- Ground truth dos cenários separa features injetadas de efeitos mecânicos (`secondary_features`); S1 regerado com lotes idênticos.

### Corrigido
- Leitura do PSI do score fora do tempo (F2): o 0,226 era artefato do filtro de maturação; errata no ADR-0006 e model card corrigido.

### Achados
- Diagnóstico certo em 100% dos lotes alertados nos cenários com ground truth; atraso de 2 (S1), 5 (S2), 3 (S3) e 0 (S4) lotes.
- No dado real, o drift de entrada aparece em 2014 e a confirmação com rótulo só em 2017–2018.
- Degradação com rótulo fica em SEV-1 nos cenários S2 e S3, o que afeta o desenho do modo conservador (F7).

## F4 — Simulador de cenários de degradação (2026-11-13)

### Adicionado
- Cenários configuráveis em `config/scenarios/` (validados por Pydantic): S0 controle, S1 choque econômico (D1), S2 concept drift no DTI alto (D3), S3 prior shift (D2), S4 bug de unidade em 30% das linhas (D6) e S5 produção natural (2014–2018).
- Motor de simulação ([ADR-0017](docs/adr/0017-scenario-simulator.md)): amostragem do holdout com seed por lote, transformações de mundo real, de bug e de mecanismo do rótulo; parcela recalculada pela amortização; rótulo por oráculo que preserva P(Y|X) quando só X muda; atraso de rótulo.
- Todos os lotes passam pelo quality gate da F3 e são pontuados pelo champion; manifesto de ground truth por cenário em `docs/evidence/scenarios/` e RUN record do tipo `sim`.
- `make simulate [SCENARIO=S2]`; `docs/SCENARIOS.md` com narrativa econômica e resultados.

### Alterado
- `amortized_installment` extraída do contrato para ser reutilizada pelo simulador.
- Gerador de lote sintético dos testes movido para `tests/synthetic.py`.

### Achados
- Com o limiar 0,495, a taxa de aprovação é um sinal fraco: o choque pleno do S1 a move em 1,7 p.p.; o sinal de saída precisa vir da distribuição do score (F5).
- S2 e S3 elevam o bad rate em 5 a 7 p.p. com score e aprovação parados: só o desempenho com rótulo enxerga.
- S4 derruba a aprovação em 6 p.p. sem mudar a inadimplência e escapa do contrato, como previsto.

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
