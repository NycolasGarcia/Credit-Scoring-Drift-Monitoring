# ADR-0011 — Severidade e política de alertas

- **Status:** aceito
- **Data:** 2026-11-15
- **Fase:** F6

## Contexto

A F5 entregou um motor de severidade por sinal (SEV-0 a 3), com cortes calibrados em `config/monitoring/thresholds.yaml` ([THRESHOLDS.md](../THRESHOLDS.md), [ADR-0018](0018-l4-sev2-cut.md)). A F6 precisa transformar isso em alertas visíveis, cada um com dono, playbook e ação (§8.1, princípio 6), e acrescentar os alertas operacionais: contrato, etapa que falha, lentidão e monitor parado.

Escrever as regras do Prometheus com os limiares em PromQL duplicaria cada corte em dois lugares, que divergiriam no primeiro ajuste. O ADR-0018 mudou um corte dois dias depois da calibração.

## Decisão

1. **Uma fonte de verdade para os cortes.**
   - O job avalia a severidade em Python (`src/monitoring/severity.py` com `thresholds.yaml`) e o nível de cada alerta (`src/alerting/engine.py` com `config/monitoring/alerts.yaml`).
   - O job publica o resultado como `cdm_alert_level{alert=<id>}`, de 0 a 3.
   - As regras do Prometheus só testam `cdm_alert_level >= 1`, e o rótulo `severity` é derivado do valor (`SEV-{{ $value }}`). Nenhum limiar aparece em PromQL.
2. **Catálogo declarativo:**
   - `alerts.yaml` define cada alerta com id, origem (sinal do detector, contrato, etapa, duração, assinatura D6), camada, diagnóstico (§8.2), ação (§8.5), dono e âncora de playbook.
   - Dele são gerados as regras (`monitoring/rules/cdm_alerts.yml`) e o catálogo `docs/ALERTS.md`, ambos com teste de sincronia.
3. **Um alerta por sinal, com severidade dinâmica**, em vez de um alerta por (sinal, nível). Um sinal que piora de SEV-1 para SEV-2 é o mesmo alerta mudando de nível, não dois alertas.
4. **Alertas operacionais (§8.4):**
   - **Lote bloqueado:** SEV-2, e SEV-3 com 2 lotes bloqueados seguidos (fonte quebrada).
   - **Regra de aviso do contrato:** SEV-1.
   - **Etapa que falha:** SEV-2.
   - **Duração:** SEV-1 quando passa de 2× a mediana dos lotes anteriores do run.
   - **Assinatura de bug de unidade (D6):** SEV-2.
5. **Dead man's switch (GR-11):** é a única regra avaliada só no Prometheus, porque trata da ausência do job. Dispara em SEV-3 quando `time() − cdm_last_success_timestamp_seconds` passa de 2× o intervalo esperado entre execuções.
   - O intervalo é configurável: 15 s no replay, um mês em produção mensal.
   - A regra não dispara antes do primeiro run: um monitor que nunca rodou não tem o que perder de vista.
6. **Sem `for:` nas regras de sinal.** Cada lote é uma observação completa, então esperar N avaliações seguidas só atrasaria o alerta sem reduzir ruído; o ruído já foi tratado na calibração.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Limiares escritos direto em PromQL | Regras autocontidas no Prometheus | Cada corte duplicado em PromQL e YAML; o ADR-0018 já mudou um corte | Divergência garantida |
| Uma regra por (sinal, nível) | Rótulo de severidade estático | Um mesmo problema vira 2–3 alertas simultâneos | Fadiga de alerta |
| Alertas só no Python (sem Prometheus) | Mais simples | Sem dead man's switch (ausência não se detecta de dentro do job) e sem histórico de alertas no painel | GR-11 exige um observador externo |
| `absent()` no dead man's switch | Detecta também o monitor que nunca rodou | Dispara em toda stack recém-criada | Ruído na demonstração; o caso "nunca rodou" fica no runbook |

## Consequências

**Boas:**
- Mudar um limiar é mudar o YAML e recalibrar. Prometheus, painel e logs mostram o mesmo nível, porque todos leem o mesmo número.
- Todo alerta tem diagnóstico, ação e playbook declarados, e o teste falha se algum faltar.

**Ruins / custos aceitos:**
- **Mais um gauge por lote:** o Prometheus não sabe *por que* o nível é 2, só *que* é 2. O porquê fica nos logs, no MLflow e nos outros gauges do painel.
- **Dead man's switch depende de configuração:** seu intervalo muda entre replay e produção; o valor errado vira ruído ou silêncio.

## Como saberemos que a decisão estava errada

- **Divergência de nível:** um alerta no Prometheus discorda do nível registrado no log e no MLflow do mesmo lote.
- **Ruído no controle:** um replay do S0 dispara alerta de sinal (o portão da F6 exige 0 SEV-2+ no S0).
- **Falha do dead man's switch:** ele não dispara quando o replay é interrompido.

## Referências

- `config/monitoring/alerts.yaml`, `src/alerting/`, `monitoring/rules/cdm_alerts.yml`, [ALERTS.md](../ALERTS.md), [RUNBOOK.md](../RUNBOOK.md)
- §8.4, §8.5, §8.6 (GR-11)
