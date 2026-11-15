# ADR-0010 — Stack de observabilidade e replay

- **Status:** aceito
- **Data:** 2026-11-15
- **Fase:** F6

## Contexto

O job de monitoramento é batch: pontua um lote mensal e termina, antes de qualquer *scrape*. A saúde do modelo precisa aparecer num painel, com alertas que levam a ações (R3, RO-13, RO-14), sem nuvem e sem credencial de terceiro (§1).

Fatos verificados nesta fase (NV-13, com contêineres das versões fixadas):
- **Pushgateway v1.11.1 rejeita amostras com timestamp:** HTTP 400, "pushed metrics must not have timestamps". Não dá para empurrar um lote de 2014 com data de 2014.
- **O `promtool` do Prometheus v3.5.0 tem backfill** (`tsdb create-blocks-from openmetrics`), mas gera blocos de TSDB offline. As regras de alerta são avaliadas no instante corrente, então os dados retroativos aparecem nos gráficos sem gerar nenhum alerta.

## Decisão

1. **Métricas:**
   - O job publica gauges com `prometheus-client` no **Pushgateway**, com grupo `job=cdm_monitoring, scenario=<id>`; cada push substitui o estado do grupo.
   - O **Prometheus** coleta do Pushgateway (`honor_labels`) e avalia as regras de alerta.
   - O **Grafana** lê o Prometheus.
2. **Painel como código:**
   - Datasource e dashboard provisionados por arquivo (`monitoring/grafana/provisioning/`).
   - O JSON do dashboard é gerado por `src/observability/dashboard.py`, com teste de sincronia.
   - Os prints do painel vêm do `grafana-image-renderer` (API de render do Grafana), sem navegador manual.
3. **Logs:**
   - JSON por linha, com o filtro de privacidade (GR-10), em `logs/<run_id>.jsonl`.
   - Cada etapa de cada lote emite um evento estruturado (`run_id`, `batch_id`, `step`, `status`, `duration_ms`, `rows_in`, `rows_out`, `rows_quarantined`).
   - O arquivo vai também como artefato do MLflow.
4. **MLflow:** o experimento `monitoring` tem um run pai por execução de cenário, com o log, o resumo e o HTML do Evidently como artefatos, e um run filho por lote, com as métricas.
5. **Replay em tempo real:** `make replay SCENARIO=S1` processa um lote a cada `INTERVAL` segundos (padrão 15), publicando o estado do lote. O eixo do tempo no Grafana é o tempo do replay; o mês simulado vai num gauge (`cdm_batch_index`) e num rótulo de informação (`cdm_batch_info{issue_month}`).
6. **Compose:**
   - Imagens com tag fixa (Prometheus v3.5.0, Pushgateway v1.11.1, Grafana 12.1.1, renderer v4.0.10).
   - Portas ligadas a `127.0.0.1`.
   - Senha do Grafana vinda do `.env`, exigida para administrar. A leitura do painel é anônima (papel Viewer, só leitura), para o painel abrir direto e os prints saírem pelo renderer sem que nenhuma credencial circule em script.
   - Contêineres sem root.
7. **Sem Alertmanager.** Não há a quem notificar num ambiente local. Os alertas ficam visíveis no Prometheus (`/alerts`) e no painel, pela série `ALERTS`.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Backfill com `promtool` (timestamps de 2014–2018) | Eixo do tempo = mês real | Blocos offline; as regras de alerta não avaliam dados retroativos | Os alertas, que são metade de R3, não disparariam |
| Exportador HTTP no próprio job (*pull*) | Sem Pushgateway | O job termina antes do scrape (§11.8) | Perderia o estado do último lote |
| Evidently UI | Relatórios navegáveis | Segunda interface, sem regras de alerta nem saúde do pipeline | Os relatórios HTML já são evidência da F5 |
| Datadog / nuvem | Gerenciado | Conta e chave de terceiro (§1, §17) | Fora do escopo |
| Loki para logs | Busca de logs no Grafana | Mais um serviço; os logs já são JSON estruturado por run | Sem ganho para a rubrica; o arquivo por run + artefato MLflow basta |
| Alertmanager | Roteamento e silenciamento | Não há destino de notificação local | Sem uso real; os alertas ficam visíveis no Prometheus e no painel |

## Consequências

**Boas:**
- Os alertas disparam de verdade, avaliados pelo Prometheus, durante o replay.
- Tudo sobe com `make stack-up`, sem credencial externa, e o painel nasce provisionado.
- O mesmo evento estruturado alimenta log, MLflow e métrica.

**Ruins / custos aceitos:**
- **Eixo de tempo artificial:** o eixo é o tempo do replay, não o mês. Um replay do S5 inteiro (60 lotes) leva ~15 min com o intervalo padrão.
- **Estado só do último lote:** o Pushgateway guarda só o último estado de cada grupo. O histórico vive no TSDB do Prometheus enquanto o volume existir, e no MLflow.

## Como saberemos que a decisão estava errada

- Um replay não consegue mostrar no painel, sem intervenção manual, um alerta disparando e sendo resolvido.
- O tempo de replay inviabiliza a demonstração do vídeo; nesse caso, reduzir o intervalo ou reavaliar o backfill para os gráficos.

## Referências

- NV-13 (verificado nesta fase), §11.8, §17.5
- `docker-compose.yml`, `monitoring/`, `src/observability/`, `src/pipeline.py`
