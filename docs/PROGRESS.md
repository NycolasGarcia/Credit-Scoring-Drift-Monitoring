# Progresso

Log append-only de checkpoints. Cada entrada registra o snapshot numérico, as evidências e o veredito da fase.

---

## CHECKPOINT — F0 «Scaffolding, fundação e travas de publicação» · fechamento · 2026-11-12

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-0.1 | Instalação limpa funciona | ok | Clone novo + `uv sync --frozen` + lint + testes verdes |
| HR-0.2 | ruff sem erros | ok | `ruff check .` → All checks passed; `ruff format --check .` → 18 files already formatted |
| HR-0.3 | CI verde | **parcial** | Workflow `.github/workflows/ci.yml` criado; os mesmos passos rodaram verdes no clone limpo. Execução no GitHub depende do primeiro push (ação do autor). Exceção justificada abaixo |
| HR-0.4 | Estrutura de `docs/` criada | ok | `docs/README.md`, `PROGRESS.md`, `ARCHITECTURE.md`, templates de ADR/RUN/INC, `runs/INDEX.md` |
| HR-0.5 | Travas de publicação ativas e demonstradas | ok | Ver demonstração abaixo + `tests/test_publication.py` |

### Portões numéricos

| Portão | Alvo | Medido | Status |
|---|---|---|---|
| `ruff check .` | 0 erros | 0 | ok |
| `make test` | verde | 28 passed | ok |
| `uv sync --frozen` em ambiente limpo | OK | OK (clone novo) | ok |
| CI no GitHub | verde | não executado (sem remoto) | pendente |
| Guarda rejeita isca proibida | bloqueia | 3/3 iscas bloqueadas e revertidas | ok |
| Arquivos locais de trabalho fora de `git ls-files` | 0 | 0 | ok |

**Demonstração do bloqueio (HR-0.5), executada no repositório real e revertida:**

1. Arquivo de dado forçado (`git add -f data/raw/bait.csv`) → `forbidden path pattern`, commit abortado.
2. Arquivo da denylist local forçado → `path in local denylist` + `denylisted string`, commit abortado.
3. Mensagem `wip` → `commit message is not Conventional Commits`, commit abortado.

O HEAD não mudou após as três tentativas.

### Estado

- Caixas da fase: 11/11 → micro 100% (0.8 com execução remota pendente; ver exceção)
- Progresso macro: 2%
- Rubrica tocada: R3 (fundação de logging estruturado)
- ADRs aceitos: ADR-0001, ADR-0002
- RUNs registrados: nenhum (fase sem execução de modelo)
- Limiares: 0 CALIBRADO · 0 PROPOSTO (arquivo ainda não criado)
- Incidentes abertos: nenhum
- Travas de publicação: OK

### Achados

- `evidently==0.7.23` não importa com `pandas 3.x` (`ImportError: infer_dtype_from_object`). O pandas foi fixado em 2.3.3 (ADR-0001). Isso confirma na prática o risco de instabilidade de API.
- O `.gitignore` com `data/` e `models/` sem âncora ignorava também `src/data/` e `src/models/`. Corrigido para `/data/` e `/models/`, com teste de regressão na guarda.

### Exceção justificada

HR-0.3 (CI verde no GitHub) fica pendente porque o repositório ainda não tem remoto, e criar remoto ou fazer push é ação exclusiva do autor. Os passos idênticos do workflow (sync congelado, lint, format, testes, guarda em arquivos e no histórico) rodaram verdes num clone limpo. O primeiro push fecha o portão; se o CI falhar, isso tem prioridade sobre o trabalho de fase.

### Veredito

**PODE AVANÇAR para F1**, com a pendência de HR-0.3 registrada acima.

---

## Nota — 2026-11-12 · fechamento da exceção HR-0.3

Repositório remoto criado (privado) e primeiro push feito. O CI rodou **verde** em todos os passos (lint, testes, guarda nos arquivos e no histórico). Em seguida, as actions foram atualizadas para o runtime Node 24 e o runner foi fixado em `ubuntu-24.04` (commit `ci:`), por aviso de depreciação do próprio CI. **HR-0.3: ok.**

---

## CHECKPOINT — F1 «Dados, alvo e separação referência × produção» · fechamento · 2026-11-12

Convenção adotada nesta fase: números de dados (não de modelo) citam como fonte o notebook de EDA e/ou `docs/evidence/data/split_manifest.json`, ambos amarrados ao sha256 do arquivo bruto (`3eae03c2…f36a`). RUN records começam na F2, com os runs de treino.

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-1.0 | NV-1 a NV-7 fechados | ok | NV-1, 2, 5, 6, 7 verificados; NV-3 e NV-4 fechados como irrelevantes ou parciais (alternativa descartada). Dois NVs novos abertos (dicionário de terceiros; estabilidade das colunas de bureau), mitigados empiricamente |
| HR-1.1 | ≥ 5.000 amostras, alvo binário | ok | Referência 107.843 rotulados (bad rate 15,60%) |
| HR-1.2 | ADR-0003, 0004, 0005 aceitos | ok | `docs/adr/0003…0005` |
| HR-1.3 | Allowlist sem coluna pós-originação (teste) | ok | `tests/test_inventory_features.py` |
| HR-1.4 | Interseção referência × produção = 0 (teste) | ok | `tests/test_target_split.py` |
| HR-1.5 | Inventário PII completo | ok | `config/data/column_inventory.yaml`, 151/151 colunas, conferido contra o cabeçalho real |

### Portões numéricos

| Portão | Alvo | Medido | Status |
|---|---|---|---|
| Amostras rotuladas na referência | ≥ 5.000 | 107.843 | ok |
| Bad rate por safra calculado | sim | 2007–2018, resolvidos × maduros | ok |
| Colunas pós-originação na allowlist | 0 | 0 | ok |
| Ids na interseção entre partições | 0 | 0 | ok |
| Hashes registrados e reprodutíveis | sim | 4/4 partições idênticas em 2 execuções | ok |
| Colunas no inventário | 100% | 151/151 | ok |
| ruff / testes | 0 / verde | 0 / 47 passed | ok |

### Estado

- Caixas da fase: 11/11 → micro 100%
- Progresso macro: 5% (F0 2 + F1 3)
- Rubrica tocada: R1 (2) · R2 (1) · RO-7, RO-17
- ADRs aceitos: ADR-0003, ADR-0004, ADR-0005
- RUNs registrados: nenhum (fase de dados)
- Limiares: 0 CALIBRADO · 0 PROPOSTO
- Incidentes abertos: nenhum
- Travas de publicação: OK

### Achados

- **As features de bureau só existem a partir de 2013.** Isso definiu a referência = safra 2013.
- **A censura do rótulo está quantificada:** bad rate entre resolvidos supera o dos maduros em +3,9 pp (2014), +5,3 pp (2015) e +7,2 pp (2016).
- **Há drift natural forte em 2018** contra 2013: `verification_status` PSI 0,47, `percent_bc_gt_75` 0,41, `revol_util` 0,40, `bc_util` 0,39, `int_rate` 0,27. O S5 terá sinal real.
- **Aparecem categorias novas** na produção (`home_ownership` ANY/NONE, `purpose` educational). São insumo para o contrato soft da F3.
- **O loader lia 33 linhas de rodapé como válidas** (string vazia ≠ nulo no pyarrow). Corrigido, com teste.

### Veredito

**PODE AVANÇAR para F2.**

---

## Nota — 2026-11-12 · revisão de sincronia de docs da F1

Revisão pós-fechamento a pedido do autor. A partir daqui, toda mudança atualiza os docs no mesmo ciclo, e cada CHECKPOINT ganha a linha "Docs em sincronia".

Corrigido:

- `docs/ARCHITECTURE.md`: fluxo real da preparação de dados (mermaid), tabela de componentes por módulo e configuração versionada.
- `README.md`: passos para obter o dataset, criar o `.env` e rodar `make data`, `make eda` e `make inventory`.
- `make help`: lista todos os alvos, agrupados.
- `notebooks/01_eda.ipynb`: tabela de status por safra agora sobre aplicações individuais (mesma base do data card) e cardinalidade das categóricas por safra (caixa 1.6 completa).
- `docs/data_card.md`: % Current na base individual e cardinalidade.
- ADR-0004: errata de um percentual citado (59% → 58% em 2017, base individual); a decisão não muda.

Novas salvaguardas: `tests/test_docs_sync.py` falha se um módulo de `src/` não estiver no ARCHITECTURE ou se um alvo do Makefile não estiver no `make help`.

Pendente do autor: aval da convenção de fonte para números de dados da F1 (notebook/manifesto com hash do bruto em vez de RUN-id).

Docs em sincronia: **ok**.

---

## CHECKPOINT — F2 «Modelo baseline, calibração e perfil de referência» · fechamento · 2026-11-12

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-2.1 | ≥ 3 runs no MLflow com RUN record | ok | RUN-20261112-train-REF-01/02/03 (todos de árvore limpa) |
| HR-2.2 | ≥ 4 métricas por run | ok | AUC, Gini, KS, PR-AUC, Brier, log-loss, bad rate esperado/observado (test e OOT) |
| HR-2.3 | Todo candidato supera o Dummy | ok | AUC test: LogReg 0,7001 · XGBoost 0,6979 · Dummy 0,5000; garantido por `select_champion` |
| HR-2.4 | OOT reportado | ok | OOT 2014 e 2015 maduros, em todos os runs |
| HR-2.5 | Modelo calibrado e registrado como `champion` | ok | `credit-scoring` v1 @champion (RUN-…-REF-02); calibração Platt ajustada e reportada |
| HR-2.6 | `reference_profile.json` versionado | ok | Artefato MLflow do run REF-02; sha256 `ffcfdc1b0b85d6cc…f75e9` |

### Portões numéricos

| Portão | Alvo | Medido | Fonte | Status |
|---|---|---|---|---|
| Runs de treino | ≥ 3 | 3 | REF-01..03 | ok |
| AUC candidato > Dummy | todos | 0,7001 / 0,6979 > 0,5000 | REF-01..03 | ok |
| OOT reportado | sim | 2014 e 2015 | REF-02 | ok |
| Brier pós ≤ pré (champion) | ≤ | 0,12253509 > 0,12253362 (+1,5×10⁻⁶) | REF-02 | **não** (exceção abaixo) |
| Perfil de referência com hash | sim | sha256 registrado | REF-02 | ok |
| AUC < 0,90 (auditoria de vazamento) | < 0,90 | 0,7001 | REF-02 | ok |
| Reprodutibilidade do treino | mesmos números | run de depuração e run oficial idênticos | — | ok |
| ruff / testes | 0 / verde | 0 / 74 passed | — | ok |

### Estado

- Caixas da fase: 11/11 → micro 100%
- Progresso macro: 8% (F0 2 + F1 3 + F2 3)
- Rubrica tocada: R1 (3) · RO-6
- ADRs aceitos: ADR-0006, ADR-0007
- RUNs registrados: RUN-20261112-train-REF-01, -02 (champion v1), -03
- Limiares: 0 CALIBRADO · 0 PROPOSTO em `thresholds.yaml` (criado na F5); premissas de custo PROPOSTO em `config/models/cost.yaml`
- Incidentes abertos: nenhum
- Travas de publicação: OK
- Docs em sincronia: ok (ARCHITECTURE, README, docs/README, model card, EXPERIMENTS gerado)

### Achados

- **Calibração neutra.** A LogReg já sai calibrada (esperado 15,50% × observado 15,58% no teste), e a recalibração de Platt não muda o Brier além do ruído. No XGBoost, a isotônica **piorou** o Brier (+2,4×10⁻⁴).
- **Degradação natural fora do tempo, antes de qualquer simulação.** Observado/esperado vai de 1,006 (2013) a 1,113 (2014) e 1,287 (2015), com AUC estável perto de 0,69–0,70. O PSI do score em 2015 é 0,226, puxado pela queda de `int_rate`. Isso dá o padrão "ranking preservado, calibração quebrada" (D2) com dado real, que é insumo para F4 (S5), F5 (L3/L4) e F7 (recalibração).
- **Empate técnico LogReg × XGBoost** (ΔAUC 0,0022): a LogReg venceu pela estabilidade, conforme a regra do ADR-0006.
- **APIs do MLflow 3.18 diferentes do esperado:** backend padrão SQLite e serialização por skops com tipos confiáveis. Adotada uma lista explícita de tipos em vez de pickle.
- **Bug no registro de reprodutibilidade, encontrado e corrigido.** Escrever um RUN record alterava o índice versionado e marcava os runs seguintes como sujos. Agora o estado do git é capturado no início do job (commit `fix(reporting)` + teste). Os runs inválidos foram descartados antes de qualquer commit.

### Exceção justificada

O portão "Brier pós ≤ pré" é PROPOSTO e falha por 1,5×10⁻⁶. O objetivo do portão, um modelo calibrado para o monitoramento comparar esperado × observado, é atendido: |esperado − observado| = 0,08 pp no teste. **Proposta ao autor:** reformular o portão como "|bad rate esperado − observado| ≤ 1 pp no teste".

### Pendências do autor

- Aval da convenção de fonte de números da F1.
- Aval da reformulação do portão de calibração.
- Premissas de custo (LGD 0,60; margem 0,50) continuam PROPOSTO.

### Veredito

**PODE AVANÇAR para F3**, com a exceção do portão de calibração registrada acima.

---

## Nota — 2026-11-13 · decisões do autor e revisão pós-F2

**Aprovado pelo autor:**

1. **Convenção de fonte para números de dados.** Números sobre dados que não dependem de modelo (contagens, bad rate por safra, PSI exploratório) podem citar o notebook de EDA ou `docs/evidence/data/split_manifest.json`, desde que amarrados ao sha256 do arquivo bruto. Números de modelo, monitoramento e resposta continuam exigindo RUN-id.
2. **Portão de calibração reformulado.** "Brier pós ≤ pré" foi substituído por **"|bad rate esperado − observado| ≤ 1 pp no teste"**. Medido no champion (RUN-20261112-train-REF-02): 15,50% × 15,58% = **0,08 pp → ok**. A exceção da F2 está **encerrada**.

**Achado — robustez do limiar (ADR-0007):** a sensibilidade às premissas de custo (notebook `02_modelagem`, seção 4) deu limiar ótimo entre 0,06 e 0,55 e aprovação entre 14% e 100%. Ele fica dentro de 0,25–0,40 em apenas 6 das 25 combinações de LGD ∈ [0,4; 0,8] × margem ∈ [0,3; 0,7]. **O sinal de reversão do ADR-0007 disparou.** O limiar vigente (0,33) continua em uso. Recomendação ao autor: estimar LGD e realização de margem **do próprio dado**, em agregado, nos empréstimos maduros da referência (`recoveries`/`total_pymnt` para LGD; `total_rec_int`/juros contratuais para margem). Essas colunas pós-originação seriam usadas só para parametrizar custo, nunca como feature. Depois, registrar um ADR que supersede o 0007. Decisão pendente do autor.

Docs em sincronia: **ok** (ADR-0007 com nota explícita, model card, ARCHITECTURE).

---

## Nota — 2026-11-13 · EDA aprofundada, validação da EDA e validação de custo FP/FN

**Validação da EDA existente**, por cálculo independente direto do CSV bruto, sem o loader de `src/`:

| Verificação | Resultado |
|---|---|
| Total de empréstimos | 2.260.668 |
| Individuais | 2.139.958 |
| Ids duplicados | 0 |
| Bad rate 2013 / 2016 (resolvidos) | 15,60% / 23,26% |
| % Current 2017 | 58,3% |
| Referência + holdout | 134.804 linhas, bad rate 15,60% |

Tudo bate com o notebook e com o manifesto. O notebook não tem células com erro, não tem células não executadas e não vaza ids reais.

**Lacunas encontradas e fechadas** (`notebooks/01_eda.ipynb`, seções 8–15):

- estatística descritiva com skew e curtose;
- regras de qualidade por safra (impossíveis, utilização > 100%, parcela incoerente, **sentinela `tot_hi_cred_lim` = 9.999.999**);
- outliers (3·IQR e extremos);
- histogramas + KDE de referência × produção;
- bad rate por decil e Information Value;
- Pearson × Spearman (matrizes, pares redundantes, divergências não lineares, correlação com o alvo);
- padrões temporais mensais;
- economia realizada.

Dois problemas corrigidos durante a revisão: um aviso do pandas expunha um caminho local nas saídas, e as cores da figura de KDE não batiam com a legenda.

**Validação de custo FP/FN** ([RUN-20261113-calib-COST-01](runs/RUN-20261113-calib-COST-01.md), reprodutível):

- Premissas medidas no caixa realizado: LGD **0,327**, realização de juros **0,756**.
- O limiar vigente 0,33 tem **regret de 8,1%** no teste contra o ótimo realizado.
- Com premissas empíricas, a curva de valor modelada reproduz a realizada (Pearson 0,999; regret 0,05%).
- Nesta população já aprovada pelo credor, o ótimo econômico é aprovar quase todos até ~8% a.a. de custo de funding.

Decisão registrada como **ADR-0016 (proposto)**, com opções A–D e recomendação B + D. O inventário ganhou o uso `custo` para as colunas de pagamento, com teste garantindo que nunca chegam ao modelo nem ao loader.

Pendente do autor: decisão do ADR-0016.

Docs em sincronia: **ok** (data card, model card, ADR-0007/0016, índice, ARCHITECTURE, README, data_inventory).

---

## Nota — 2026-11-13 · ADR-0016 aceito (B + D) e champion v2

**Decisão do autor:** opção B (premissas medidas + funding declarado) combinada com a opção D (apetite de risco como guardrail). O ADR-0016 supersede o ADR-0007.

Sequência executada, com árvore limpa em cada run:

1. **Código.** A economia modelada passou a cobrar funding sobre o saldo-ano de cada desfecho. Entrou a premissa nova de realização de juros dos maus. A config ganhou `funding_rate`, `source_run` e `risk_appetite`.
2. **[RUN-20261113-calib-COST-02](runs/RUN-20261113-calib-COST-02.md)** estimou as premissas: LGD 0,327, juros dos bons 0,756, juros dos maus 0,564. Com funding de 5%, o limiar fica em 0,495 e o regret em 0,88%. As premissas antigas com funding teriam regret de 71%.
3. **Config.** `config/models/cost.yaml` passou para status ESTIMADO, com `source_run` = COST-02.
4. **[RUN-20261113-train-REF-02](runs/RUN-20261113-train-REF-02.md)** registrou o **champion v2**: mesmo modelo, AUC 0,7001, **limiar 0,495**. No teste, aprovação de 99,8%, bad rate dos aprovados 15,5% e US$ 942 por proposta.
5. **[RUN-20261113-calib-COST-03](runs/RUN-20261113-calib-COST-03.md)** validou a config adotada: regret de **0,88%**, abaixo do sinal de reversão de 2%, e aderência de 0,9986.
6. **Apetite de risco.** O teto de bad rate dos aprovados de 14% ficou registrado como PROPOSTO, para o modo conservador (GR-4) da F7.

**Leitura:** em regime normal o modelo aprova quase todos, por causa do viés de seleção da base. O valor do modelo aparece sob degradação. Isso vira tema explícito do vídeo e da F7.

Docs em sincronia: **ok** (ADR-0016 aceito, ADR-0007 supersedido, índice, model card v2, notebook `02_modelagem` reexecutado, EXPERIMENTS regenerado).

---

## CHECKPOINT — F3 «Contratos de dados e quality gate» · fechamento · 2026-11-13

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-3.1 | Contrato Pandera com ≥ 3 regras rígidas (meta ≥ 8) | ok | 11 regras hard de entrada (H01–H11) + 3 de saída (O01–O03); `docs/DATA_CONTRACTS.md` |
| HR-3.2 | Lote ruim bloqueado ponta a ponta com evidência | ok | `make validate-bad`: 13 defeitos → bloqueado, 0 linhas pontuadas, exit 2, alerta `CONTRACT_BATCH_BLOCKED` (`docs/evidence/contracts/bad-all-seed7.json`) |
| HR-3.3 | Cada regra com teste que a faz falhar isoladamente | ok | `tests/test_contracts.py`: 13 defeitos parametrizados + testes diretos de S01/S03/S04/O01–O03; um teste garante que toda regra do catálogo tem teste |
| HR-3.4 | Quarentena com relatório de violação sem PII | ok | `report.json` só com agregados; teste verifica que nenhuma chave nem valor de linha aparece |
| HR-3.5 | ADR-0008 aceito | ok | `docs/adr/0008-data-contracts.md` |

### Portões numéricos

| Portão | Alvo | Medido | Status |
|---|---|---|---|
| Regras hard | ≥ 3 (meta ≥ 8) | 11 de entrada + 3 de saída | ok |
| Regras com teste de falha isolada | 100% | 18/18 | ok |
| Lote ruim → linhas pontuadas | 0 | 0 | ok |
| Relatório lista regra e contagem por defeito | sim | 11 regras com contagem (linhas distintas) | ok |
| Valores PII no relatório | 0 | 0 (teste) | ok |
| Falso bloqueio em lotes reais | — | 0/61 (holdout + 60 meses); quarentena máx. 0,049% | ok |
| ruff / testes | 0 / verde | 0 / 110 passed | ok |

### Estado

- Caixas da fase: 10/10 → micro 100%
- Progresso macro: 28% (F0 2 + F1 3 + F2 3 + F3 20)
- Rubrica tocada: R1 (20) · RO-1, RO-8, RO-12
- ADRs aceitos: ADR-0008
- RUNs registrados: nenhum (o gate não depende de modelo novo; evidências agregadas em `docs/evidence/contracts/`)
- NV fechado: NV-12 (Pandera 0.36 verificado na versão fixada)
- Limiares: 0 CALIBRADO · 0 PROPOSTO em `thresholds.yaml` (F5); tolerância de linhas do contrato (1%) é PROPOSTO
- Incidentes abertos: nenhum
- Travas de publicação: OK
- Docs em sincronia: ok (`DATA_CONTRACTS.md` gerado e testado, ARCHITECTURE com o fluxo do gate, README, índice)

### Achados

- **Gate em dois níveis em vez do GR-1 literal.** Lotes reais trazem defeitos esparsos por linha (parcela incoerente, sentinela em 13 meses, renda de US$ 110 mi). Bloquear o lote por qualquer linha ruim barraria quase todos os meses. Linhas ruins vão para quarentena, e o bloqueio fica reservado a falha estrutural ou a mais de 1% de linhas ruins.
- **Falso positivo do próprio contrato, encontrado nos lotes reais:** `term` é inteiro no dado e o contrato esperava float. Corrigido no contrato (`integer_columns`).
- **Pandera reporta checagem de DataFrame uma vez por coluna** de cada linha reprovada. A contagem por regra passou a ser por linhas distintas.
- **Os valores brutos aparecem nos casos de falha do Pandera.** O relatório descarta esses valores; só contagens são publicadas.
- **D6 (renda mensal):** o contrato (`H10`, mediana do lote) só bloqueia quando ≥ 50% das linhas estão erradas. O PSI de `annual_inc` passa de 0,23 a partir de 20% (`docs/evidence/contracts/d6_sweep.json`). Contrato e drift são camadas complementares, e a separação D1 × D6 fica para a F5.

### Veredito

**PODE AVANÇAR para F4.**

---

## CHECKPOINT — F4 «Simulador de cenários de degradação» · abertura · 2026-11-13

Entrada: F3 fechada, CI verde em `2d523b1`, travas OK, nenhum incidente aberto. Escopo: S0–S5 com manifesto, determinismo e pontuação de todos os lotes. ADR exigido: ADR-0017. Nenhum NV aberto bloqueia a fase. Rubrica: R2 (10) · RO-2, RO-11.

## CHECKPOINT — F4 «Simulador de cenários de degradação» · fechamento · 2026-11-13

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-4.1 | ≥ 2 variáveis importantes driftadas (RO-11) | ok | S1: `int_rate` (1ª em importância), `annual_inc` (3ª), `dti` (9ª); [RUN-20261113-sim-S1-01](runs/RUN-20261113-sim-S1-01.md) |
| HR-4.2 | Cenário de controle sem drift | ok | S0, [RUN-20261113-sim-S0-01](runs/RUN-20261113-sim-S0-01.md) |
| HR-4.3 | ≥ 1 concept drift com mecanismo de rótulo | ok | S2: logit + 1,0 no DTI ≥ p70, rótulo visível 3 lotes depois; [RUN-20261113-sim-S2-01](runs/RUN-20261113-sim-S2-01.md) |
| HR-4.4 | Manifesto de ground truth por cenário | ok | `docs/evidence/scenarios/S0.json` … `S5.json` |
| HR-4.5 | Determinismo por seed | ok | `test_same_seed_same_hash_different_seed_differs`; S2 regerado no dado real com hashes idênticos nos 12 lotes |
| HR-4.6 | Predições para todos os lotes | ok | 108/108 lotes pontuados pelo gate (0 bloqueados) |

### Portões numéricos

| Portão | Alvo | Medido | Status |
|---|---|---|---|
| Features driftadas em S1 | ≥ 2 | 3 | ok |
| Cenários com manifesto | S0–S4 (+ S5) | 6/6 | ok |
| Determinismo | verde | verde (teste + dado real) | ok |
| Predições | 100% dos lotes | 108/108 | ok |
| ruff / testes | 0 / verde | 0 / 123 passed | ok |

### Estado

- Caixas da fase: 12/12 → micro 100%
- Progresso macro: 38% (F0 2 + F1 3 + F2 3 + F3 20 + F4 10)
- Rubrica tocada: R2 (10) · RO-2, RO-11
- ADRs aceitos: ADR-0017
- RUNs registrados: RUN-20261113-sim-S0-01 … S5-01
- Limiares: 0 CALIBRADO · 0 PROPOSTO em `thresholds.yaml` (F5)
- Incidentes abertos: nenhum
- Travas de publicação: OK
- Docs em sincronia: ok (SCENARIOS.md com teste de sincronia, ARCHITECTURE com fluxo e módulos, README, índice, CHANGELOG)

### Achados

- **A taxa de aprovação é um sinal fraco neste modelo.** O choque pleno de S1 a move em 1,7 p.p., abaixo da faixa SEV-1 proposta (± 3 p.p.). A camada L3 da F5 precisa usar o PSI do score.
- **Degradação silenciosa reproduzida:** S2 e S3 elevam o bad rate em 5 a 7 p.p. com score e aprovação parados.
- **S4 escapa do contrato, como desenhado,** e derruba a aprovação em 6 p.p. sem alterar a inadimplência: o custo do bug é recusar bons pagadores.
- **Censura em S5:** 0% de rótulo a partir de 2017; o bad rate de 2016 vem de 20,8% da safra.
- **Erro operacional corrigido durante a fase:** uma verificação de determinismo sobrescreveu o manifesto oficial do S2 e o índice de RUNs ainda não commitado. O manifesto foi restaurado da cópia e as linhas do índice foram reconstruídas dos próprios RUN records, conferidas contra a saída original.

### Veredito

**PODE AVANÇAR para F5.**

---

## CHECKPOINT — F5 «Detecção de drift e avaliação do detector» · abertura · 2026-11-13

Entrada: F4 fechada, CI verde em `a337f7f`, travas OK, nenhum incidente aberto. Escopo: L2/L3/L4 por lote, relatório Evidently por cenário, calibração no S0, avaliação contra os manifestos. ADR exigido: ADR-0009. NV a fechar: NV-8 (API do Evidently), NV-9 (PSI como convenção), NV-10 (p-valor com N grande). Rubrica: R2 (14) · RO-2, RO-3, RO-9.

## CHECKPOINT — F5 «Detecção de drift e avaliação do detector» · fechamento · 2026-11-13

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-5.1 | Relatório Evidently HTML por cenário apontando as features driftadas | ok | `docs/evidence/drift/S0..S5_evidently.html`; S1 aponta `int_rate`, `dti`, `annual_inc` e o score; S4 aponta `annual_inc` e o score |
| HR-5.2 | PSI e KS próprios cruzados com o Evidently | ok | `psi_ref` no Evidently = PSI próprio (diferença 0,000000 nas colunas sem nulos, 6 relatórios); KS e Wasserstein embutidos = scipy (testes) |
| HR-5.3 | Limiares calibrados em S0, falso alarme medido | ok | [RUN-20261113-calib-S0-01](runs/RUN-20261113-calib-S0-01.md): 6 limiares CALIBRADO; falso alarme composto 0,2% (SEV-1+) e 0% (SEV-2+) |
| HR-5.4 | Concept drift (S2) detectado por L4 | ok | S2: L2/L3 nunca alertam; L4 no lote 8, D3 em 5/5, segmento `dti` ([RUN-20261113-monitor-S2-01](runs/RUN-20261113-monitor-S2-01.md)) |
| HR-5.5 | ADR-0009 aceito | ok | `docs/adr/0009-drift-detection-methodology.md` |
| HR-5.6 | RUN records de todos os cenários | ok | monitor S0-01, S1-02, S2-01, S3-01, S4-01, S5-02 (todos de árvore limpa) |

### Portões numéricos

| Portão | Alvo | Medido | Fonte | Status |
|---|---|---|---|---|
| Features injetadas em S1 apontadas | 100% | 3/3 (precisão 100%) | monitor-S1-02 | ok |
| Falso alarme em S0 | ≤ 5% SEV-1, 0% SEV-2+ | 0/12 lotes; bootstrap 0,2% / 0% | monitor-S0-01, calib-S0-01 | ok |
| Detection delay por cenário | reportado | S1 2 · S2 5 · S3 3 · S4 0 lotes | DRIFT_EVALUATION | ok |
| S2: L2 quieto e L4 alarmando | sim | sim | monitor-S2-01 | ok |
| S4 classificado como D6 | sim | 7/7 lotes, fator 12 | monitor-S4-01 | ok |
| HTML Evidently por cenário | 6 | 6 | `docs/evidence/drift/` | ok |
| ruff / testes | 0 / verde | 0 / 151 passed | — | ok |

### Estado

- Caixas da fase: 11/11 → micro 100%
- Progresso macro: 52% (F0 2 + F1 3 + F2 3 + F3 20 + F4 10 + F5 14)
- Rubrica tocada: R2 (14) · RO-2, RO-3, RO-9
- ADRs aceitos: ADR-0009 (+ errata no ADR-0006)
- RUNs registrados: calib-S0-01; monitor S0-01, S1-01→S1-02, S2-01, S3-01, S4-01, S5-01→S5-02; sim S1-02→S1-03
- NV fechados: NV-8, NV-9, NV-10
- Limiares: 6 CALIBRADO · 0 PROPOSTO (meta de falso alarme e parâmetros D6 seguem PROPOSTO)
- Incidentes abertos: nenhum
- Travas de publicação: OK
- Docs em sincronia: ok (THRESHOLDS e DRIFT_EVALUATION gerados e testados; ARCHITECTURE, README, índice, model card, CHANGELOG)

### Achados

- **Diagnóstico 100% certo nos cenários com ground truth:** D1 (S1), D3 (S2, com o segmento `dti` identificado), D2 (S3), D6 (S4).
- **O sinal antecipado chega três anos antes da confirmação.** No S5, o drift de entrada aparece em 2014, mas a L4 só existe a partir de 2017 (vencimento dos contratos de 36 meses), quando observado/esperado sobe até 1,39 com o ranking preservado (D2).
- **A degradação com rótulo fica em SEV-1.** S2 e S3 têm razão observado/esperado de no máximo 1,37 e 1,499, abaixo do SEV-2 (1,5). Um circuit breaker só em SEV-2 não dispararia: a questão foi aberta para o autor (§15) antes da F7.
- **Errata da F2:** o PSI do score de 0,226 no OOT 2015 era um artefato do filtro de maturação (só contratos de 36 meses); na população inteira de 2015 é 0,009. ADR-0006 recebeu errata e o model card foi corrigido.
- **Correções feitas durante a fase:**
  - **Ground truth do S1:** passou a separar as features injetadas da parcela recalculada (efeito mecânico). O S1 foi regerado com lotes idênticos.
  - **Severidade:** valor absoluto em todos os sinais fazia AUC que melhora disparar alerta; agora a direção é declarada por sinal.
  - **NaN no JSON e RUN órfão:** um NaN no JSON derrubou a primeira detecção oficial depois de o RUN record ter sido escrito. O resíduo foi limpo, e o JSON passou a ser validado antes do RUN.
  - **RUN de árvore suja:** a detecção do S1, rodada logo após regerar o cenário, encontrou a árvore suja. Foi descartada e repetida após o commit da geração.

### Veredito

**PODE AVANÇAR para F6.**

---

## CHECKPOINT — F6 «Observabilidade: logs, métricas, dashboard e alertas» · abertura · 2026-11-15

Entrada: F5 fechada, CI verde em `b6c6d96`, travas OK, nenhum incidente aberto. Escopo: job de monitoramento ponta a ponta com eventos por etapa, métricas via Pushgateway, Prometheus + Grafana como código, regras de alerta com dead man's switch, replay de cenários. ADRs exigidos: ADR-0010 (stack), ADR-0011 (severidade e alertas). NVs de que depende: NV-13 (replay no Prometheus), NV-14 (reuso da stack do TC3). Rubrica: R3 (14) · RO-3, RO-13, RO-14.

**Decisão antes do trabalho da fase — SEV-2 da razão observado/esperado** ([ADR-0018](adr/0018-l4-sev2-cut.md)). A questão aberta na F5 (a degradação com rótulo ficava em SEV-1) foi resolvida por análise, sem ajustar o corte aos cenários de avaliação:

1. **Regra declarada antes da execução** em `config/monitoring/l4_sweep.yaml`: o menor corte com 0% de alarme nulo e folga ≥ 0,10 sobre o máximo nulo.
2. **[RUN-20261115-calib-L4CUT-01](runs/RUN-20261115-calib-L4CUT-01.md):** máximo nulo 1,103 (coortes de 6.000) e 1,192 (2.000). Corte escolhido: **1,25**, com 0% de alarme nulo nos dois tamanhos.
3. **Validação em variantes novas** (seeds 201–203): nas intensidades oficiais de S2 e S3, a detecção em SEV-2 passa de 0/3 (corte 1,5) para 3/3 (corte 1,25). O concept drift fraco (logit +0,5) segue em SEV-1.
4. **Detecção refeita** (RUN-20261115-monitor-S0-01 … S5-01): sinais e diagnósticos idênticos. Muda só a severidade dos lotes com L4 (S2 4 lotes, S3 5, S4 4, S5 9). S2 e S3 chegam a SEV-2 no primeiro alerta.
5. O custo econômico de agir com esse corte é verificado na F7 (caixa 7.9), que pode rever o ADR-0018.

## CHECKPOINT — F6 «Observabilidade: logs, métricas, dashboard e alertas» · fechamento · 2026-11-15

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-6.1 | Logs de execução centralizados (sucesso/falha por etapa + resultados de drift) | ok | `logs/<run_id>.jsonl`, um evento por etapa e lote; artefato do run pai no MLflow; exemplo versionado em `docs/evidence/observability/run_log_S4.jsonl` (96 eventos, só agregados) |
| HR-6.2 | MLflow com runs de monitoramento + dashboard Grafana como código | ok | Experimento `monitoring`: RUN-20261115-monitor-S0-03 … S5-03 (108 runs por lote + HTML do Evidently no run pai); `monitoring/grafana/dashboards/cdm_monitoring.json` gerado e testado |
| HR-6.3 | Métricas de saúde documentadas (status, latência, volume, alertas) | ok | [METRICS.md](METRICS.md): 22 gauges, com status e duração por etapa, linhas por estágio e alertas por severidade |
| HR-6.4 | Alertas disparados e visíveis | ok | `docs/evidence/observability/alerts_fired.json` e `all_alertas_disparados.png`; prints por cenário |
| HR-6.5 | ADR-0010 e ADR-0011 aceitos | ok | `docs/adr/0010-observability-stack.md`, `docs/adr/0011-severity-alert-policy.md` |

### Portões numéricos

| Portão | Alvo | Medido | Fonte | Status |
|---|---|---|---|---|
| Serviços do Compose | healthy | 4/4 (Pushgateway, Prometheus, Grafana, renderer) | `make stack-status` | ok |
| Alvos do Prometheus | UP | 2/2 | `/api/v1/targets` | ok |
| Painéis com dados | ≥ 6 | 13 (5 indicadores + 8 gráficos) | prints por cenário | ok |
| Alerta de cada severidade | ≥ 1 por SEV | SEV-1 (S1 score), SEV-2 (S1 feature, S2/S3 bad rate), SEV-3 (dead man's switch) | `alerts_fired.json` | ok |
| SEV-2+ no S0 | 0 | 0 (nenhum alerta) | RUN-20261115-monitor-S0-02 | ok |
| Dead man's switch | demonstrado | `promtool test rules` + disparo real após o replay | CI, `all_alertas_disparados.png` | ok |
| Métricas de RO-14 | status, latência, volume, alertas | todas | METRICS.md | ok |
| Regras | `promtool check` + `test` | 11 regras, testes verdes | `make check-rules`, CI | ok |
| ruff / testes | 0 / verde | 0 / 179 passed | — | ok |

### Estado

- Caixas da fase: 12/12 → micro 100%
- Progresso macro: 66% (F0 2 + F1 3 + F2 3 + F3 20 + F4 10 + F5 14 + F6 14)
- Rubrica tocada: R3 (14) · RO-3, RO-13, RO-14
- ADRs aceitos: ADR-0010, ADR-0011 (e ADR-0018 na abertura)
- RUNs registrados: calib-L4CUT-01; monitor S0-01 … S5-01 (redetecção com o corte novo); monitor S0-02 … S5-02 (replays); monitor S0-03 … S5-03 (job com MLflow correto)
- NV fechados: NV-13 (verificado), NV-14 (não utilizado: stack montada do zero)
- Limiares: 6 CALIBRADO · 0 PROPOSTO
- Incidentes abertos: nenhum
- Travas de publicação: OK
- Docs em sincronia: ok (METRICS, ALERTS, regras, testes do promtool e dashboard gerados e testados; RUNBOOK, ARCHITECTURE, README, índice, CHANGELOG)

### Achados

- **O dead man's switch disparou entre os replays.** Cada transição entre cenários (prints, commit, carga do modelo) passou de 30 s sem lote concluído. É a semântica correta do GR-11: o monitor estava de fato parado. A regra ficou global (sem rótulo de cenário) depois que o primeiro teste mostrou que, por cenário, cada fim de replay gerava um "monitor parado" falso.
- **Bug: runs por lote no experimento errado.** Carregar o champion depois de abrir o run pai trocava o experimento ativo do MLflow, e os 120 runs por lote dos replays foram para o `training`.
  - **Correção:** contexto montado antes, `experiment_id` explícito e teste de regressão.
  - **Limpeza:** os 120 runs foram removidos do `training` (exclusão lógica).
  - **Refeito:** o job rodou de novo em modo `monitor` (-03), com resumos idênticos aos dos replays.
- **Grafana com leitura anônima** (Viewer, só em 127.0.0.1). Assim, os prints saem do renderer sem que nenhuma credencial circule em script; a administração continua exigindo a senha do `.env` (ADR-0010).
- **Correção da F5:** no S2, o diagnóstico D3 cobre 4 de 4 lotes alertados (do 8 ao 11), não "5 de 5" como dizia a leitura. A acurácia de 100% não muda.
- **Duração do job:** mediana de 1,6 s por lote nos simulados e 2,9 s no S5; `detect` é a etapa dominante.
- **S5 dispara a regra de aviso do contrato (SEV-1)** em parte dos meses reais. Fica registrado; a investigação da regra específica vai para o game day da F7.

### Veredito

**PODE AVANÇAR para F7.**

## CHECKPOINT — F7 «Resposta à degradação: guardrails, playbooks e retreino controlado» · abertura · 2026-11-15

> Registrada em 2026-11-17, junto com o fechamento: a abertura não foi escrita no dia em que a fase começou. O conteúdo abaixo reconstitui o veredito de entrada a partir do fechamento da F6 e do primeiro commit da fase.

1. **Pré-requisitos:** F6 fechada com veredito "PODE AVANÇAR"; SEV-2 da razão observado/esperado em 1,25 (ADR-0018), o que faz S2 e S3 chegarem a SEV-2, condição para um circuit breaker em SEV-2.
2. **ADRs previstos:** 0012 (guardrails e modo conservador) e 0013 (retreino, gate e rollback).
3. **Dependência aberta:** NV-11 (base legal da revisão de decisão automatizada) segue como hipótese até a F8.

## CHECKPOINT — F7 «Resposta à degradação: guardrails, playbooks e retreino controlado» · fechamento · 2026-11-17

### Hard requirements

| HR | Descrição | Status | Evidência |
|---|---|---|---|
| HR-7.1 | Todos os GR de §8.6 implementados e testados | ok | GR-1/2 (`test_contracts`, `test_blocked_batch_skips_scoring_and_raises_contract_alert`), GR-3/4 (`test_policy_matrix_rows`, `test_breaker_opens_and_closes_after_cool_down`), GR-5 (`test_gate_rejects_a_worse_challenger`), GR-6 (`test_promote_then_rollback_restores_and_is_reversible`), GR-7/8 (`test_training_refuses_*`), GR-9 (`test_kill_switch_*`), GR-10 (`test_run_log_file_is_json_lines_without_pii`), GR-11 (`test_staleness_is_prometheus_only` + `promtool test rules`) |
| HR-7.2 | Matriz §8.5 executável (policy engine), não só documentada | ok | `config/response/policy.yaml` + `src/response/policy.py`, aplicada pela etapa `respond` do job a cada lote |
| HR-7.3 | Champion/challenger com gate (GR-5) e rollback (GR-6) demonstrados | ok | [RUN-20261115-response-DRILL-01](runs/RUN-20261115-response-DRILL-01.md): gate aprovado na sombra no lote 9; rollback restaura e é reversível; registry real intacto (champion v2) |
| HR-7.4 | Comparação de respostas com custo por cenário | ok | [RESPONSE_EVALUATION.md](RESPONSE_EVALUATION.md), [RUN-20261117-response-ALL-01](runs/RUN-20261117-response-ALL-01.md) |
| HR-7.5 | ≥ 1 game day com postmortem INC-0001 | ok | [INC-0001](incidents/0001-s2-concept-drift-dti.md), [RUN-20261117-gameday-S2-01](runs/RUN-20261117-gameday-S2-01.md) |
| HR-7.6 | ADR-0012 e ADR-0013 aceitos | ok | e também 0019, 0020, 0021 e 0022 |

### Portões numéricos

| Portão | Alvo | Medido | Fonte | Status |
|---|---|---|---|---|
| GR com teste | 100% | 11/11 | suíte (ver HR-7.1) | ok |
| Gate rejeita challenger pior | ≥ 1 em teste | teste sintético + S1 (evitou −US$ 109 mil) | `test_gate_rejects_a_worse_challenger`, RUN-20261117-response-ALL-01 | ok |
| Rollback em 1 comando | `make rollback` | troca de aliases, reversível | RUN-20261115-response-DRILL-01 | ok |
| Tabela de respostas com custo | S1, S2, S3, S4 | 4/4 | RUN-20261117-response-ALL-01 | ok |
| INC-0001 fechado com itens de ação | sim | fechado; 5 itens (3 feitos na F7, 2 abertos com dono) | INC-0001 | ok |
| ruff / testes | 0 / verde | 0 / 218 passed | — | ok |
| Regras do Prometheus | `promtool check` + `test` | não reexecutado (Docker parado); `monitoring/rules/` sem mudança desde o fechamento da F6 | `git diff cc52835 HEAD -- monitoring/rules` vazio | ok |

### Estado

- Caixas da fase: 13/13 → micro 100%
- Progresso macro: 73% (F0 2 + F1 3 + F2 3 + F3 20 + F4 10 + F5 14 + F6 14 + F7 7)
- Rubrica tocada: R3 (4) · R4 (3) · prescrição da Etapa 4
- ADRs aceitos: 0012, 0013, 0019 (supersede o item 3 do 0012), 0020 (supersede o critério de calibração do 0013), 0021 (altera o item 4 do 0012), 0022 (supersede o item 6 do 0013)
- RUNs registrados: response-ALL-01 e ALL-02 de 2026-11-15 (substituídos), response-DRILL-01, gameday-S2-01, response-ALL-01 de 2026-11-17
- Limiares de detecção: 6 CALIBRADO · 0 PROPOSTO. Parâmetros da resposta (histerese de 2 lotes, capacidade da fila de 15%, janelas e volumes mínimos do ciclo de vida, critérios do gate) seguem PROPOSTO
- Incidentes abertos: nenhum (INC-0001 fechado; itens 3 e 5 abertos com dono)
- Travas de publicação: OK
- Docs em sincronia: ok (ARCHITECTURE, README, índice de docs, RUNBOOK, RESPONSE_EVALUATION gerado e testado, ADRs com notas de status, CHANGELOG)

### Achados

- **A resposta certa depende do diagnóstico, e a matriz acerta qual é** (RUN-20261117-response-ALL-01):
  - **D3 (S2):** o modo conservador por valor rende +US$ 2,94 mi.
  - **D2 (S3):** rende +US$ 2,66 mi, e a recalibração, sozinha, +US$ 0,87 mi.
  - **D1 (S1):** a política não age, e é o certo.
  - **D6 (S4):** a quarentena retém o lote; forçar o modo conservador sobre o bug custaria US$ 6,3 mi.
- **O teto de 14% do apetite de risco destruía valor** (−US$ 1,25 mi no S2, −US$ 2,95 mi no S3) e foi trocado pelo corte de valor esperado com risco corrigido (ADR-0019, decisão do autor).
- **O gate absoluto de calibração reprovava challengers estritamente melhores** que o champion; passou a ser relativo (ADR-0020). Com isso, o challenger do S2 é aprovado e rende +US$ 0,61 mi.
- **Game day (INC-0001):** diagnóstico D3 no segmento `dti` correto contra o ground truth; modo conservador automático no lote do alerta; challenger aprovado no gate no lote seguinte. Quatro problemas do sistema apareceram:
  - **Árvore errada para concept drift:** a árvore de decisão separava D2 de D3 pela AUC, que não cai nesse tipo de concept drift. Corrigida na triagem do RUNBOOK.
  - **A6 declarada sem existir:** a matriz declarava A6 automática sem que o job a executasse. Agora é humana, com comando (ADR-0022).
  - **Fila sem dimensão:** a fila de revisão não tinha capacidade declarada. Agora tem 15% do lote, com o excedente recusado (ADR-0021); o ganho do modo conservador deixa de depender do revisor (+US$ 1,07 mi no S2 e +US$ 2,13 mi no S3 mesmo com a fila decidida depois como o champion decidiria).
  - **Rampa sem aviso:** a rampa do concept drift passou sem SEV-1. Fica como item de ação 3.
- **Doc fora de sincronia corrigido no fechamento:** a leitura humana da comparação ainda dizia que o gate reprovava o challenger do S2, o que deixou de ser verdade com o ADR-0020.
- **Pendência herdada da F6 não coberta:** a investigação da regra de aviso do contrato que dispara no S5 estava prevista para o game day, mas o game day foi feito no S2. Fica para a F8, junto com a análise causal da produção natural.

### Veredito

**PODE AVANÇAR para F8.**
