# ADR-0002 — Política de publicação e higiene do repositório

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F0

## Contexto

O projeto manipula dados de crédito, credenciais (Kaggle, chave de pseudonimização, senha do Grafana) e artefatos grandes (modelos, runs do MLflow, relatórios). Um único `git add` descuidado publica dado pessoal ou segredo, e remover do histórico depois não desfaz a exposição. O autor também mantém arquivos de trabalho locais que não fazem parte do entregável.

## Decisão

Defesa em camadas, todas ativas antes do primeiro commit:

1. **Exclusão local não versionada** (`.git/info/exclude`) para arquivos de trabalho do autor. O `.gitignore` versionado cobre só padrões genéricos (dados, modelos, logs, segredos).
2. **Denylist local** (`.git/info/publish-denylist`, nunca versionada) com caminhos e termos proibidos específicos do autor.
3. **`scripts/check_publication.py`**, genérico e versionado. Bloqueia:
   - caminhos de dados/artefatos/segredos (`data/`, `models/`, `mlruns/`, `logs/`, `reports/`, `.env`, `kaggle.json`, `*.csv`/`*.parquet` fora de `tests/fixtures/`);
   - arquivos acima de 1 MB (exceto `docs/evidence/`);
   - padrões de segredo (chave privada, tokens);
   - termos da denylist local;
   - HTML de evidência com tabela de linhas individuais ou coluna PII.
4. **pre-commit**: hook `pre-commit` (ruff, `detect-private-key`, `check-added-large-files`, guarda de publicação) e hook `commit-msg` (Conventional Commits + denylist).
5. **CI** executa a guarda sobre todos os arquivos versionados e sobre o histórico inteiro.
6. Regras operacionais: `git add` sempre com caminhos explícitos; nunca `--no-verify`; push sempre feito pelo autor.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Só `.gitignore` | Simples | Não pega `git add -f`, conteúdo nem mensagem | Uma camada só |
| Ferramentas prontas (gitleaks, detect-secrets) | Cobertura ampla de segredos | Não cobrem política de dados nem evidência HTML | Podem complementar no futuro |
| Só CI | Centralizado | O segredo já foi publicado quando o CI roda | Tarde demais |

## Consequências

**Boas:** o bloqueio acontece antes do commit; o próprio teste (`tests/test_publication.py`) prova cada regra com arquivos-isca.

**Ruins / custos aceitos:** fixtures precisam ser sintéticas e pequenas; evidências HTML precisam de curadoria antes de entrar em `docs/evidence/`.

## Como saberemos que a decisão estava errada

Qualquer arquivo proibido encontrado em `git ls-files` ou no histórico (`make publish-check-history`), ou falsos positivos frequentes que levem a contornar o hook.
