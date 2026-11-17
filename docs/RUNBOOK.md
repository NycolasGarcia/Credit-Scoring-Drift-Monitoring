# Runbook

Operação da stack de observabilidade, do job de monitoramento e resposta a cada alerta. Decisões: [ADR-0010](adr/0010-observability-stack.md) (stack), [ADR-0011](adr/0011-severity-alert-policy.md) (alertas) e, para a resposta, [ADR-0012](adr/0012-guardrails-conservative-mode.md), [ADR-0013](adr/0013-retraining-gate-rollback.md), [ADR-0019](adr/0019-conservative-mode-by-value.md), [ADR-0021](adr/0021-review-queue-capacity.md) e [ADR-0022](adr/0022-challenger-shadow-human.md). Catálogos: [METRICS.md](METRICS.md) e [ALERTS.md](ALERTS.md).

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

Cada etapa emite um evento JSON com `run_id`, `batch_id`, `step`, `status`, `duration_ms`, `rows_in`, `rows_out` e `rows_quarantined`. Na etapa `respond`, `rows_out` são as aprovações e `rows_quarantined` as propostas mandadas para revisão humana.

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

## Resposta à degradação

A etapa `respond` aplica a matriz de resposta (`config/response/policy.yaml`) a cada lote. A primeira regra que casa com o diagnóstico e a severidade define as ações automáticas e humanas. Depois, a cadeia de guardrails decide cada proposta, com código de motivo:

| Código | Decisão | Quando |
|---|---|---|
| R20 | revisão | kill switch ligado (GR-9): toda decisão automática suspensa |
| R30 | revisão | quarentena preventiva do lote (suspeita de bug D6) |
| R11 | recusa | modo conservador com a fila de revisão cheia: excedente de pior valor esperado |
| R10 | revisão | modo conservador (GR-4): o champion aprovaria, mas o valor esperado com o risco corrigido não é positivo |
| R01 | recusa | score acima do limiar do champion |
| R00 | aprovação | score abaixo do limiar do champion |

### Controles sem deploy

O arquivo da política é relido a cada lote; a mudança vale a partir do lote seguinte.

| Campo | Efeito | Quando usar |
|---|---|---|
| `kill_switch: true` | Tudo vai para revisão (A9) | SEV-3 sem diagnóstico, ou desconfiança geral do modelo |
| `conservative_mode: on` / `off` | Força o modo conservador ligado ou desligado, acima do circuit breaker | `on`: degradação conhecida antes do alerta; `off`: alarme comprovadamente falso |
| `dry_run: true` | Calcula e registra as ações, mas decide como o champion puro | Ensaiar uma política nova |
| `conservative.review_capacity` | Fração do lote que a fila de revisão aceita (15%, PROPOSTO) | Ajustar à capacidade real da equipe de revisão |

Toda mudança nesses campos é decisão humana: registrar no incidente aberto, com o motivo.

### Comandos

```bash
make gameday-watch SCENARIO=S2              # job lote a lote na visão do operador; para no 1º alerta SEV-2+ (UNTIL_SEV, LIMIT)
make gameday-shadow SCENARIO=S2 AT=8        # A6: challenger treinado no lote AT, em sombra nos lotes seguintes
make gameday SCENARIO=S2                    # execução completa do game day, com evidência e RUN record
make respond-compare                        # valor de cada resposta por cenário → docs/RESPONSE_EVALUATION.md
make respond-drill                          # sombra + ensaio de promoção e rollback no registry de ensaio
make rollback                               # GR-6: troca os aliases champion e champion_previous
make rollback REGISTRY=credit-scoring-drill # o mesmo, no registry de ensaio
```

As saídas de `gameday-watch` e `gameday-shadow` vão para `logs/<id>.view.json`, que contém só agregados por lote.

### Triagem de um alerta (árvore de decisão)

Seguir na ordem; a primeira resposta "sim" decide:

1. **O contrato bloqueou o lote ou uma etapa falhou (L0/L1)?** É dado ou pipeline (D0/D5). Corrigir a fonte. Não tocar no modelo.
2. **Há `CDM_UNIT_BUG_SUSPECTED`, ou a mudança é abrupta, num lote só, com fator constante?** Suspeita de D6. Quarentena (automática) e confirmação com a fonte. Nunca retreinar.
3. **Drift de entrada (L2) sem drift de score ou de aprovação (L3)?** D1 benigno. Registrar e revisar no ciclo seguinte.
4. **Drift de score ou aprovação (L3) com rótulo ainda imaturo?** Modo conservador (automático em SEV-2) e análise causal.
5. **Rótulo maduro disponível (L4).** Olhar a razão observado/esperado, a AUC madura e o gap por segmento (`segment_feature`, `segment_gap` no log):
   - **Descolamento concentrado num segmento (D3)**, com ou sem queda de AUC: challenger em sombra (`make gameday-shadow`) e gate. **A AUC sozinha não separa D2 de D3:** no game day do S2 ([INC-0001](incidents/0001-s2-concept-drift-dti.md)), o concept drift no DTI alto não derrubou a AUC.
   - **Descolamento uniforme, sem segmento dominante, com a AUC estável (D2):** recalibrar (A5).
   - **Tudo estável:** falso alarme. Registrar e revisar o limiar com um RUN `calib`.

### Game day

Ensaio de incidente com um cenário simulado:

1. Rodar `make gameday-watch` sem abrir o manifesto do cenário.
2. No primeiro alerta SEV-2+, abrir `docs/incidents/INC-<nnnn>` com o horário, a partir do template.
3. Seguir a triagem e o playbook do alerta **como estão escritos**. Se o playbook estiver errado ou incompleto, registrar como achado; não corrigir durante o incidente.
4. Executar a ação e verificar o efeito no lote seguinte: `make gameday-watch UNTIL_SEV=0 LIMIT=<lote + 2>` processa até o lote seguinte (os lotes começam em 0). O job é determinístico, então reprocessar desde o início equivale a continuar.
5. Só então abrir `docs/evidence/scenarios/<cenário>.json` e comparar o diagnóstico com o ground truth.
6. Rodar `make gameday` para o RUN record e escrever o postmortem; os itens de ação viram tarefas ou ADRs.

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

Regra geral, pela [triagem](#triagem-de-um-alerta-árvore-de-decisão): primeiro descartar dado ou pipeline quebrado (L0/L1), depois bug de unidade (D6). Só então tratar como drift ou degradação do modelo. Cada playbook diz o que a política já fez sozinha (**Automático**), o que olhar, o que fazer e quando escalar. Toda ação humana é registrada no incidente aberto.

### CDM_CONTRACT_BLOCKED

- **Significa:** o contrato bloqueou o lote. Houve falha estrutural ou mais de 1% de linhas inválidas, e nenhuma linha foi pontuada (GR-1).
- **Automático:** regra P01. O lote fica em quarentena (A2) e o alerta sai (A1).
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
- **Automático:** regra P02. Quarentena preventiva do lote inteiro: toda proposta vai para revisão com o motivo R30.
- **Olhar:** `unit_bugs` no log do lote (feature, fator, excesso na cauda) e o painel "PSI por feature e lote".
- **Fazer:** confirmar com a fonte e, depois do conserto, reprocessar os lotes retidos. **Nunca retreinar** sobre esse dado (GR-7) e **nunca forçar o modo conservador** (`conservative_mode: on`): sobre o bug, ele custaria US$ 6,3 mi no S4, contra +US$ 4,0 mi de reter e decidir depois do conserto ([RESPONSE_EVALUATION.md](RESPONSE_EVALUATION.md)). O diagnóstico D6 tem precedência sobre qualquer alerta de modelo no mesmo lote.
- **Escalar:** sempre ao dono da integração; a correção é na fonte.

### CDM_FEATURE_DRIFT

- **Significa:** o PSI de uma feature passou do corte. SEV-1 vale para qualquer feature; SEV-2 exige uma feature do top-10; SEV-3, três delas.
- **Automático:** com o score estável, regra P09: só registrar (A0). A política de crédito não muda por drift de entrada.
- **Olhar:** o painel "PSI por feature e lote" (quais features) e "Score e aprovação" (se a decisão mudou).
- **Fazer:** com o score estável, é D1 benigno: registrar e revisar no ciclo seguinte. Com o score também em drift, seguir `CDM_SCORE_DRIFT`.
- **Escalar:** SEV-3, ou um drift que coincide com `CDM_UNIT_BUG_SUSPECTED`.

### CDM_SCORE_DRIFT

- **Significa:** a distribuição do score mudou (PSI contra os decis da referência).
- **Automático:** em SEV-2 com diagnóstico D1/D4, regra P07: modo conservador (A4).
- **Olhar:** "Score e aprovação", "Resposta à degradação" e as features em drift no mesmo lote.
- **Fazer:** confirmar que não é bug de dado; abrir incidente e análise causal (A3). Se o diagnóstico for de bug, desligar o modo conservador (`conservative_mode: off`) até a fonte ser confirmada.
- **Escalar:** SEV-2 persistente por mais de um lote.

### CDM_APPROVAL_SHIFT

- **Significa:** a taxa de aprovação se afastou da referência além da banda (± 3, 7 e 12 p.p.).
- **Olhar:** "Score e aprovação" e o diagnóstico do lote. No S4, por exemplo, a queda de aprovação veio do bug de unidade.
- **Automático:** em SEV-2 com diagnóstico D1/D4, regra P07: modo conservador (A4).
- **Fazer:** descartar D6 primeiro. Sem bug, abrir incidente e análise causal (A3).
- **Escalar:** SEV-3 (± 12 p.p.).

### CDM_BAD_RATE_RATIO

- **Significa:** nos rótulos que amadureceram, o bad rate observado descolou do esperado. O sinal é simétrico: subestimar e superestimar o risco contam igual.
- **Automático:** em SEV-2, regra P03 (D3) ou P05 (D2): modo conservador por valor (A4), com o risco corrigido pela razão medida e a fila de revisão limitada a 15% do lote. Em SEV-1 (P04, P06), nada muda na decisão.
- **Olhar:** "Desempenho com rótulo maduro", "Resposta à degradação" e o diagnóstico. D2 indica descolamento uniforme; D3, descolamento concentrado num segmento (`segment_feature` e `segment_gap` no log). A AUC estável **não** descarta D3.
- **Fazer:**
  - **D3:** abrir incidente (A3) e treinar o challenger em sombra no lote do alerta (A6): `make gameday-shadow AT=<lote>`. Acompanhar o gate (GR-5) nos lotes seguintes; quando ele passar, a promoção (A7) é decisão humana, registrada no incidente.
  - **D2:** recalibrar (A5). O efeito esperado está em `make respond-compare`; nesta versão não há comando que registre o modelo recalibrado em produção, então a aplicação é manual e registrada.
  - **Fila de revisão:** acompanhar a fração de recusas R11. Se a equipe de revisão não dá conta nem dos 15%, reduzir `review_capacity`; o valor do modo conservador não depende da revisão ([ADR-0021](adr/0021-review-queue-capacity.md)).
- **Escalar:** SEV-3 (razão ≥ 2).

### CDM_AUC_DROP

- **Significa:** a ordenação do modelo piorou nos rótulos que amadureceram.
- **Automático:** depende do diagnóstico do lote; com D3 em SEV-2, regra P03 (modo conservador).
- **Olhar:** "Desempenho com rótulo maduro" e se há bug de dado no mesmo período: no S4, o bug também derrubou a AUC.
- **Fazer:** descartar D6. Depois, challenger em sombra (`make gameday-shadow AT=<lote>`) e gate, como em `CDM_BAD_RATE_RATIO` com D3.
- **Escalar:** SEV-2 ou mais.

### Promoção e rollback

Não é um alerta, e sim o fim do caminho de D3:

- **Promover (A7):** só com o gate aprovado na sombra e decisão humana registrada no incidente. A promoção move o alias `champion` para a versão nova e guarda a anterior em `champion_previous`.
- **Rollback (GR-6):** `make rollback` troca os dois aliases. Usar quando o modelo promovido piora o desempenho no período seguinte. O próprio rollback é reversível (rodar de novo desfaz).
- **Ensaio:** `make respond-drill` exercita promoção e rollback no registry `credit-scoring-drill`, sem tocar o champion real.

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
