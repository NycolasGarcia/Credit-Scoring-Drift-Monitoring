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
