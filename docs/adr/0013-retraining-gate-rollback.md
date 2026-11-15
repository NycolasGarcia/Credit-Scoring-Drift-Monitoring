# ADR-0013 — Recalibração, retreino com gate de promoção e rollback

- **Status:** aceito (parâmetros PROPOSTO em `config/response/lifecycle.yaml`); **critério de calibração do gate supersedido pelo [ADR-0020](0020-relative-calibration-gate.md)** em 2026-11-15
- **Data:** 2026-11-15
- **Fase:** F7

## Contexto

Quando a degradação se confirma com rótulo maduro, há duas respostas de modelo: recalibrar (A5) ou treinar um challenger (A6) e promovê-lo (A7). As duas são caras de errar. Recalibrar quando era concept drift, ou retreinar em cima de bug ou de rótulo imaturo, deixa o modelo pior com aparência de correção (§7). Promover é irreversível sem um caminho de volta, então o rollback precisa existir antes da primeira promoção (§8.1, princípio 5).

## Decisão

1. **Janelas recentes.**
   - **Recalibração:** usa só a coorte madura mais recente.
   - **Challenger:** usa as 3 últimas coortes maduras.
   - **Por quê:** o primeiro protótipo, com a janela inteira, diluía a correção com rótulos de antes do drift. No S2, a razão observado/esperado só caía de 1,37 para 1,28; com a janela recente, cai para 1,08. No S3, de 1,47 para 0,99.
2. **Travas de treino** (`src/response/lifecycle.py`):
   - **GR-7:** só entram lotes com carimbo do contrato (`passed` ou `partial`), e só as linhas validadas.
   - **GR-8:** só entram rótulos já observáveis no instante da decisão (`label_batch ≤ t`).
   - **Volume mínimo:** abaixo de 8.000 linhas maduras (challenger) ou 2.000 rótulos (recalibração), o treino é recusado com `TrainingRefusedError`, e o motivo vai para o registro.
3. **Mesma receita do champion** (`training.yaml`: regressão logística e calibração sigmoid). A comparação isola o dado, não o método. A janela é dividida no tempo: o trecho mais recente fica reservado para o gate.
4. **Gate de promoção (GR-5).** Todas as condições ao mesmo tempo:

   | Condição | Critério |
   |---|---|
   | Ordenação recente | AUC na janela recente maior que a do champion |
   | Referência | não perder mais que 0,01 de AUC no teste de 2013 |
   | Calibração | \|bad rate esperado − observado\| ≤ 1 p.p. na janela recente |
   | Fairness | o gap de aprovação entre grupos de `home_ownership` não cresce mais que 3 p.p. (proxy até a F8) |

5. **Promoção e rollback (GR-6)** por aliases no MLflow Registry.
   - **Promoção:** move `champion` para a versão nova e guarda a anterior em `champion_previous`.
   - **Rollback:** `make rollback` troca os dois aliases, o que torna o próprio rollback reversível.
   - **Ensaio:** as demonstrações usam o modelo `credit-scoring-drill`, para nunca alterar o champion real durante um ensaio.
6. **Só a recusa é automática.** Treinar o challenger em sombra (A6) é automático. Promover (A7) e recalibrar em produção (A5) são decisões humanas, registradas.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Janela inteira de rótulos maduros | Mais dados | Mistura rótulos de antes do drift; corrige pouco | Medido no protótipo |
| Treinar com referência + recente | Mais estável | Dilui o regime novo no antigo | Fica como variação futura |
| Promover automaticamente se o gate passar | Mais rápido | Irreversível sem humano; contra §8.1, princípio 5 | Promoção é decisão humana |
| Gate só por AUC | Simples | Promoveria modelo descalibrado (o limiar é econômico e depende da calibração) | Calibração entra no gate |
| Retreinar a cada lote | Sempre atualizado | Aprende ruído e bug; esconde degradação | Contra §8.1, princípio 7 |

## Consequências

**Boas:**
- **O gate cumpre o papel:** nos quatro cenários, rejeitou o challenger do ponto de decisão. No S1 (D1, onde retreinar seria a resposta errada), o challenger sem gate perderia US$ 109 mil.
- **Recalibração é a resposta barata e certa para D2:** +US$ 874 mil no S3.

**Ruins / custos aceitos:**
- **Valor deixado na mesa:** no S2 o challenger sem gate renderia +US$ 609 mil, mas foi reprovado por 1,55 p.p. de descalibração. O gate é conservador por desenho; a resposta natural ali seria recalibrar o challenger antes de reavaliá-lo.
- **Retreino cedo é inviável:** no ponto de decisão quase não há rótulo maduro do regime novo (atraso de 3 lotes). Retreinar só faz sentido algumas coortes depois.
- **Proxy de fairness:** o gap por `home_ownership` substitui provisoriamente as métricas da F8.

## Como saberemos que a decisão estava errada

- **Gate frouxo:** um challenger aprovado no gate piora o desempenho no período seguinte, e é preciso fazer rollback.
- **Gate duro:** o gate reprova sistematicamente challengers que a comparação mostra como melhores; nesse caso, revisar o critério de calibração.
- **Recalibração ineficaz:** a recalibração de uma só coorte oscila demais entre lotes.

## Referências

- `config/response/lifecycle.yaml`, `src/response/lifecycle.py`, `src/response/gate.py`, `src/response/registry_ops.py`
- [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md), §8.5, §8.6 (GR-5 a GR-8)
