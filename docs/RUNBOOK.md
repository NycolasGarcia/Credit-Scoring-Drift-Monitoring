# Runbook

Operação da stack de observabilidade, do job de monitoramento e resposta a cada alerta. Decisões: [ADR-0010](adr/0010-observability-stack.md) (stack) e [ADR-0011](adr/0011-severity-alert-policy.md) (alertas). Catálogos: [METRICS.md](METRICS.md) e [ALERTS.md](ALERTS.md).

## Subir e derrubar a stack

Pré-requisitos: Docker em execução e `GRAFANA_ADMIN_PASSWORD` definido no `.env` (ver `.env.example`).

```bash
make stack-up        # Pushgateway, Prometheus, Grafana e renderer (portas só em 127.0.0.1)
make stack-status    # todos devem aparecer como healthy
make stack-down      # para os contêineres; os volumes (histórico do Prometheus) ficam
```

| Serviço | Endereço | Acesso |
|---|---|---|
| Grafana | http://127.0.0.1:3000 | leitura sem login; administração com `admin` e a senha do `.env` |
| Prometheus | http://127.0.0.1:9090 (`/alerts`, `/targets`) | local |
| Pushgateway | http://127.0.0.1:9091 | local |

Para zerar o histórico do Prometheus: `docker compose down -v`. Isso apaga os volumes.

## Rodar o job

O job lê os lotes gerados por `make simulate` (`data/simulated/<cenário>/`) e executa, para cada lote:

> ingest → validate → score → detect → evaluate → alert → respond → record

Cada etapa emite um evento JSON com `run_id`, `batch_id`, `step`, `status`, `duration_ms`, `rows_in`, `rows_out` e `rows_quarantined`. A etapa `respond` aparece como `skipped` até a política de resposta da F7.

```bash
make monitor SCENARIO=S2                  # lote a lote, sem pausa, sem publicar métricas
make replay SCENARIO=S4                   # um lote a cada INTERVAL s (padrão 15), publicando no Pushgateway
make replay SCENARIO=S4 INTERVAL=10
```

Saídas de cada execução:
- **Log da execução:** `logs/<run_id>.jsonl`, com um evento por etapa e lote, sem dado de linha (GR-10).
- **Resumo:** `logs/<run_id>.summary.json`.
- **MLflow:** experimento `monitoring`, com um run pai por execução (log e resumo como artefatos) e um run filho por lote (métricas e tags `diagnosis` e `severity`).
- **RUN record:** `docs/runs/RUN-<data>-monitor-<cenário>-<nn>.md`.

## Prints de evidência

Com a stack no ar e um replay recém-executado:

```bash
make screenshots SCENARIO=S4    # dashboard inteiro + um PNG por painel em docs/evidence/observability/
```

Os PNGs vêm do renderer do Grafana, sem login. Antes de versionar, abrir e conferir: só gráficos de gauges agregados.

## Regras de alerta

```bash
make alerts        # regenera as regras, os testes do promtool, ALERTS.md, METRICS.md e o dashboard
make check-rules   # promtool check rules + promtool test rules (Docker)
```

Mudar um limiar: editar `config/monitoring/thresholds.yaml`, rodar um novo RUN `calib` e atualizar `THRESHOLDS.md`, tudo no mesmo commit. As regras do Prometheus não mudam, porque só leem `cdm_alert_level`.

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop parado | Abrir o Docker Desktop e esperar `docker info` responder |
| `GRAFANA_ADMIN_PASSWORD` ausente ao subir | Variável não definida no `.env` | Definir a variável (ver `.env.example`) e repetir `make stack-up` |
| Etapa `record` com status `failed` no log | Pushgateway fora do ar | `make stack-status`; o lote foi processado e o log e o MLflow existem, só a métrica não foi publicada |
| Painel vazio | Cenário errado no seletor ou janela de tempo curta | Escolher o cenário no topo do painel e ampliar a janela |
| `CDM_MONITOR_STALE` disparado depois de um replay | Esperado: nenhum lote concluído há mais de 30 s | É o dead man's switch funcionando; some no próximo lote |
| Porta 3000/9090/9091 em uso | Outro serviço local | Parar o outro serviço ou mudar a porta no `docker-compose.yml` |

## Playbooks por alerta

Regra geral, pela árvore §8.7: primeiro descartar dado ou pipeline quebrado (L0/L1), depois bug de unidade (D6). Só então tratar como drift ou degradação do modelo. Cada playbook diz o que olhar, o que fazer e quando escalar. A ação automática de cada caso entra com a política de resposta da F7; até lá, toda ação abaixo é humana e registrada.

### CDM_CONTRACT_BLOCKED

- **Significa:** o contrato bloqueou o lote. Houve falha estrutural ou mais de 1% de linhas inválidas, e nenhuma linha foi pontuada (GR-1).
- **Olhar:** `data/quarantine/.../<batch_id>/report.json` (regras e contagens) e o painel "Volume e quarentena".
- **Fazer:** identificar a regra no relatório ([DATA_CONTRACTS.md](DATA_CONTRACTS.md)), corrigir na fonte e reprocessar o lote. Não pontuar manualmente.
- **Escalar:** com 2 lotes bloqueados seguidos (SEV-3), a fonte está quebrada; acionar o dono da integração.

### CDM_SOFT_RULES

- **Significa:** uma regra de aviso disparou: nulos acima da referência, categoria nova, volume fora da banda ou cauda extrema de utilização.
- **Olhar:** `soft_warnings` no relatório do lote.
- **Fazer:** registrar. Se a regra se repetir por vários lotes, revisar a fonte ou a própria regra.
- **Escalar:** se vier junto com drift de entrada na mesma feature.

### CDM_UNIT_BUG_SUSPECTED

- **Significa:** uma feature ganhou uma cauda que volta ao normal quando multiplicada por um fator de unidade (12, 52, 100 ou 1.000), a assinatura de bug upstream (D6).
- **Olhar:** `unit_bugs` no log do lote (feature, fator, excesso na cauda) e o painel "PSI por feature e lote".
- **Fazer:** quarentena preventiva dos lotes afetados e confirmação com a fonte. **Nunca retreinar** sobre esse dado (GR-7). O diagnóstico D6 tem precedência sobre qualquer alerta de modelo no mesmo lote.
- **Escalar:** sempre ao dono da integração; a correção é na fonte.

### CDM_FEATURE_DRIFT

- **Significa:** o PSI de uma feature passou do corte. SEV-1 vale para qualquer feature; SEV-2 exige uma feature do top-10; SEV-3, três delas.
- **Olhar:** o painel "PSI por feature e lote" (quais features) e "Score e aprovação" (se a decisão mudou).
- **Fazer:** com o score estável, é D1 benigno: registrar e revisar no ciclo seguinte. Com o score também em drift, seguir `CDM_SCORE_DRIFT`.
- **Escalar:** SEV-3, ou um drift que coincide com `CDM_UNIT_BUG_SUSPECTED`.

### CDM_SCORE_DRIFT

- **Significa:** a distribuição do score mudou (PSI contra os decis da referência).
- **Olhar:** "Score e aprovação" e as features em drift no mesmo lote.
- **Fazer:** com rótulo ainda imaturo e SEV-2, modo conservador (GR-4, F7) e análise causal. Antes, confirmar que não é bug de dado.
- **Escalar:** SEV-2 persistente por mais de um lote.

### CDM_APPROVAL_SHIFT

- **Significa:** a taxa de aprovação se afastou da referência além da banda (± 3, 7 e 12 p.p.).
- **Olhar:** "Score e aprovação" e o diagnóstico do lote. No S4, por exemplo, a queda de aprovação veio do bug de unidade.
- **Fazer:** descartar D6 primeiro. Com SEV-2 sem bug, modo conservador (GR-3, GR-4).
- **Escalar:** SEV-3 (± 12 p.p.).

### CDM_BAD_RATE_RATIO

- **Significa:** nos rótulos que amadureceram, o bad rate observado descolou do esperado. O sinal é simétrico: subestimar e superestimar o risco contam igual.
- **Olhar:** "Desempenho com rótulo maduro" e o diagnóstico. D2 indica descolamento uniforme; D3, descolamento concentrado num segmento (a feature aparece em `segment_feature` no log).
- **Fazer:**
  - **D2:** recalibrar (A5).
  - **D3:** challenger em sombra e gate de promoção (A6, GR-5).
- **Escalar:** SEV-3 (razão ≥ 2).

### CDM_AUC_DROP

- **Significa:** a ordenação do modelo piorou nos rótulos que amadureceram.
- **Olhar:** "Desempenho com rótulo maduro" e se há bug de dado no mesmo período: no S4, o bug também derrubou a AUC.
- **Fazer:** descartar D6. Depois, modo conservador e challenger em sombra (A4, A6).
- **Escalar:** SEV-2 ou mais.

### CDM_STEP_FAILED

- **Significa:** uma etapa do job falhou. As etapas seguintes do lote foram puladas, mas o alerta e o registro rodaram.
- **Olhar:** o evento da etapa com `status=failed` em `logs/<run_id>.jsonl`, que inclui o traceback, e o painel "Saúde do pipeline".
- **Fazer:** corrigir a causa e reprocessar o lote.
- **Escalar:** a mesma etapa falhando em dois lotes seguidos.

### CDM_PIPELINE_SLOW

- **Significa:** o lote levou mais de 2× a mediana dos lotes anteriores do mesmo run.
- **Olhar:** o painel "Duração por etapa" (qual etapa) e o volume do lote.
- **Fazer:** registrar e investigar a etapa mais lenta.
- **Escalar:** se vier acompanhado de `CDM_STEP_FAILED`.

### CDM_MONITOR_STALE

- **Significa:** nenhum lote foi concluído com sucesso há mais de 2× o intervalo esperado (dead man's switch, GR-11). Sem monitor, a ausência de alertas não significa que está tudo bem.
- **Olhar:** `make stack-status`, o processo do job e o painel "Segundos desde o último lote concluído".
- **Fazer:** restaurar o job e reprocessar os lotes perdidos. Depois de um replay de demonstração, o disparo é esperado.
- **Escalar:** sempre que não houver uma parada planejada.
