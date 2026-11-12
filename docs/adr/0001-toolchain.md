# ADR-0001 — Toolchain: uv, ruff, pytest, MLflow e versões exatas

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F0

## Contexto

O projeto precisa ser reprodutível em ambiente limpo e depende de bibliotecas com APIs instáveis entre versões (Evidently e Pandera). Na resolução inicial, o uv escolheu `pandas 3.1.1` e `evidently 0.7.23` falhou já no import (`ImportError: infer_dtype_from_object` em `pandas.core.dtypes.common`). Dependência solta quebra o projeto sem aviso.

## Decisão

- **Python 3.12** (`.python-version`, `requires-python >=3.12,<3.13`): versão com wheels estáveis para todo o stack científico.
- **uv** para ambiente e dependências; `uv.lock` versionado; `uv sync --frozen` em CI e no `make setup`.
- **Todas as dependências diretas com pino exato (`==`)** no `pyproject.toml`. Atualizar uma dependência é um commit próprio (`build:`).
- `pandas==2.3.3`, por incompatibilidade de `evidently==0.7.23` com pandas 3.x.
- **ruff** (lint + format, `max-complexity = 10`) e **pytest**; **pre-commit** executa ruff e as verificações de publicação (ADR-0002).
- **MLflow** local (backend de arquivos) para tracking e Model Registry.
- **Makefile** como interface única de comandos.

Versões fixadas: evidently 0.7.23 · pandera 0.36.0 · scikit-learn 1.9.1 · xgboost 3.4.1 · mlflow 3.18.0 · pandas 2.3.3 · numpy 2.5.4 · scipy 1.18.1 · prometheus-client 0.26.0 · pydantic 2.14.3 · pydantic-settings 2.16.2 · pyarrow 26.0.1 · pyyaml 6.0.3 · ruff 0.17.5 · pytest 9.2.0 · pre-commit 4.7.0.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| pip + requirements.txt | Universal | Sem lock de transitivas nativo, mais lento | Reprodutibilidade inferior |
| Poetry | Lock maduro | Mais lento, resolução mais pesada | uv cobre o mesmo com menos atrito |
| Pinos com faixa (`>=`) | Atualizações automáticas | Quebra silenciosa (já observada com pandas 3) | Risco comprovado |
| Python 3.13+ | Mais recente | Suporte de wheels menos garantido no stack | Sem ganho para o projeto |

## Consequências

**Boas:** ambiente idêntico em qualquer máquina e no CI; quebra de API vira decisão explícita.

**Ruins / custos aceitos:** atualizações de segurança exigem ação manual; pandas preso à série 2.x enquanto o Evidently não suportar a 3.x.

## Como saberemos que a decisão estava errada

`uv sync --frozen` falhar em ambiente limpo, ou uma versão do Evidently compatível com pandas 3 trazer recurso necessário ao projeto.
