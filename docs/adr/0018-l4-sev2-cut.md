# ADR-0018 — Corte de SEV-2 da razão observado/esperado (L4)

- **Status:** aceito
- **Data:** 2026-11-15
- **Fase:** F6 (abertura)

## Contexto

A F5 calibrou os limiares no controle ([RUN-20261113-calib-S0-01](../runs/RUN-20261113-calib-S0-01.md)). A calibração só sobe um corte quando há falso alarme, nunca o baixa. O SEV-2 da razão observado/esperado ficou no valor de planejamento, 1,5, que nunca teve base estatística.

A avaliação do detector ([DRIFT_EVALUATION.md](../DRIFT_EVALUATION.md)) mostrou que, com esse corte, a degradação real com rótulo maduro não chega a SEV-2. No S2 (concept drift) e no S3 (prior shift), o bad rate sobe de 5 a 7 p.p., mas a razão fica em no máximo 1,37 e 1,499. Como o modo conservador (GR-4) reage a SEV-2, ele não dispararia justamente na degradação silenciosa que o projeto existe para tratar.

Escolher o novo corte olhando essas razões seria ajustá-lo aos próprios cenários que vão julgá-lo. Por isso, a regra de escolha foi gravada em `config/monitoring/l4_sweep.yaml` antes da execução.

## Decisão

1. **SEV-2 da razão observado/esperado = 1,25** (era 1,5). SEV-1 (1,2) e SEV-3 (2,0) não mudam. A direção segue simétrica, max(r, 1/r).
2. **Regra de escolha, declarada antes de rodar:** o menor corte da grade (1,25 a 1,50) sem nenhuma réplica nula acima dele e com folga de pelo menos 0,10 sobre o máximo nulo. A distribuição nula vem de 2.000 coortes A/A de 6.000 propostas do holdout, com seed 31, diferente da calibração.
3. **Resultado** ([RUN-20261115-calib-L4CUT-01](../runs/RUN-20261115-calib-L4CUT-01.md)): máximo nulo 1,103, então a regra exige pelo menos 1,203, e o menor valor da grade que atende é 1,25. Com coortes de 2.000 propostas, o máximo nulo é 1,192 e o 1,25 ainda dá 0% de alarme.
4. **Validação em cenários que o corte nunca viu:** variantes de S2 e S3 com seeds novas (201–203) e três intensidades cada.

   | Variante | 1,25 | 1,50 |
   |---|---|---|
   | S2, logit +1,0 (intensidade oficial) | 3/3, atraso mediano 5 | 0/3 |
   | S3, logit +0,5 (intensidade oficial) | 3/3, atraso 3 | 0/3 |
   | S3, logit +0,25 | 2/3 | 0/3 |
   | S2, logit +0,5 | 0/3 | 0/3 |

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Manter 1,5 | Nenhuma mudança | Nas variantes novas, não detecta nenhuma das intensidades oficiais de S2/S3 | O modo conservador nunca reagiria à degradação silenciosa |
| Acionar o modo conservador com SEV-1 da L4 | Não mexe em limiar | Quebra a semântica: SEV-1 é "atenção" em todos os sinais, menos neste | Regra difícil de explicar e auditar |
| Escolher o corte pelas razões de S2/S3/S5 | Direto | Ajusta o corte aos cenários que vão avaliá-lo | Viés de seleção do limiar |
| 1,20 (igual ao SEV-1) | Detecta mais cedo | SEV-1 e SEV-2 colapsam no mesmo corte | Fica fora da grade por construção |
| Escolher pelo custo econômico de agir | É o critério certo no fim | O modo conservador ainda não existe | Fica para a F7 (caixa 7.9), que pode rever este ADR |

## Consequências

**Boas:**
- O corte tem base estatística (0% de alarme nulo com folga declarada) e foi validado em cenários que não participaram da escolha.
- S2 e S3, nas intensidades oficiais, passam a chegar a SEV-2, que é o gatilho do GR-4.

**Ruins / custos aceitos:**
- **Concept drift fraco** (logit +0,5 no segmento) continua sem SEV-2. Ele fica em SEV-1, ou seja, em atenção e revisão humana.
- **S4 (bug de unidade):** 4 lotes passam a SEV-2 pela L4, porque o bug faz o modelo superestimar o risco. O diagnóstico continua D6, que tem precedência, e o lote já estava em SEV-2 pelo drift de entrada.
- **S5 (dado real):** 9 dos 24 meses com rótulo passam a SEV-2 (descalibração real, D2). Mais alertas de recalibração.
- **Sensibilidade ao tamanho da coorte:** a folga cai para 0,06 com 2.000 rótulos (`min_labeled_rows` = 500). Coortes muito pequenas podem gerar SEV-2 por ruído.

## Como saberemos que a decisão estava errada

- **Custo:** a comparação de respostas da F7 mostra que agir com SEV-2 em 1,25 custa mais (receita recusada) do que não agir em S3 ou no S5.
- **Ruído:** uma recalibração com outra seed ou com coortes menores produz razão nula acima de 1,25.
- **Falso alarme em produção:** alertas SEV-2 de L4 em coortes que, depois, se mostram calibradas.

## Referências

- `config/monitoring/l4_sweep.yaml`, `src/monitoring/l4_sweep.py`, `docs/evidence/drift/l4_cut_sweep.json`
- [THRESHOLDS.md](../THRESHOLDS.md), [ADR-0009](0009-drift-detection-methodology.md)
