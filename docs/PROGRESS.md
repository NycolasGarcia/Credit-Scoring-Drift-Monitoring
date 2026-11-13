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
| ruff / testes | 0 / verde | 0 / 111 passed | ok |

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
