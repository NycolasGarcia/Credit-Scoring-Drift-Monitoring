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
