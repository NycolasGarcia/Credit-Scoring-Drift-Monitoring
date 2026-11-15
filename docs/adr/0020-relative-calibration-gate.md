# ADR-0020 — Critério de calibração do gate relativo ao champion

- **Status:** aceito — supersede o critério de calibração (item 4, terceira condição) do [ADR-0013](0013-retraining-gate-rollback.md)
- **Data:** 2026-11-15
- **Fase:** F7

## Contexto

O ADR-0013 exigiu que o challenger tivesse |bad rate esperado − observado| ≤ 1 p.p. na janela recente. A avaliação em sombra no S2 disparou o sinal de reversão do próprio ADR ("o gate reprova sistematicamente challengers melhores"). Em cada lote em que rótulos amadureceram, o challenger treinado no ponto de decisão foi **melhor que o champion nas duas dimensões**:
- **Ordenação:** AUC 0,005 maior.
- **Calibração:** observado/esperado entre 1,07 e 1,15, contra 1,28 a 1,37 do champion.

Mesmo assim, o gate o reprovou nos três lotes, porque o critério absoluto exige calibração que **nenhum modelo** atinge enquanto o regime ainda está mudando. O resultado era manter em produção o modelo comprovadamente pior.

## Decisão

1. **Critério relativo.** O critério de calibração passa a ser: gap do challenger ≤ max(1 p.p., gap do champion na mesma janela). Ou seja, o challenger precisa estar calibrado ou, no mínimo, não ser pior calibrado do que o modelo que vai substituir.
2. **Demais condições inalteradas:** superar o champion em AUC na janela recente, não perder mais de 0,01 de AUC na referência e não ampliar o gap de aprovação entre grupos.
3. **Promover continua sendo decisão humana (A7).** O gate só diz que a promoção é defensável.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Manter o critério absoluto (ADR-0013) | Só promove modelo bem calibrado | Mantém o pior modelo quando os dois estão descalibrados; medido no S2 | Contraria o objetivo do gate |
| Afrouxar o limite absoluto (ex.: 3 p.p.) | Simples | Número arbitrário; não compara com o modelo atual | O critério relativo responde à pergunta certa: "melhora?" |
| Exigir recalibração do challenger antes do gate | Corrige a calibração | Gasta a mesma janela de rótulos que o gate usa para avaliar | Fica como passo humano depois da promoção (A5) |

## Consequências

**Boas:**
- **O gate aprova o challenger que domina o champion:** no S2, já no primeiro lote com rótulos depois do treino (lote 9).
- **O gate continua barrando o que deve barrar:** challengers com AUC menor, que é o que acontece no S1, no S3 e no S4.

**Ruins / custos aceitos:**
- **Promoção de modelo descalibrado:** o gate pode aprovar um challenger ainda descalibrado, desde que menos que o champion. A recalibração (A5) depois da promoção vira a etapa natural.
- **Dois modelos ruins:** se o champion estiver muito descalibrado, o limite fica frouxo. A condição de AUC e a de referência continuam valendo.

## Como saberemos que a decisão estava errada

- **Ordenação:** um challenger aprovado pelo critério relativo piora a ordenação no período seguinte, e é preciso fazer rollback (GR-6).
- **Calibração:** promoções sucessivas mantêm o modelo descalibrado sem que a recalibração seja feita.

## Referências

- `docs/evidence/response/shadow_drill.json`, [RESPONSE_EVALUATION.md](../RESPONSE_EVALUATION.md)
- `src/response/gate.py`, `config/response/lifecycle.yaml`, `tests/test_lifecycle.py::test_gate_calibration_is_relative_to_the_champion`
