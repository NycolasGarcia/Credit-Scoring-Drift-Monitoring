# ADR-0022 — Challenger em sombra (A6) como ação humana

- **Status:** aceito
- **Data:** 2026-11-17
- **Fase:** F7

## Contexto

A matriz de resposta (`config/response/policy.yaml`) marcava A6, treinar um challenger e rodá-lo em sombra, como ação **automática** nas regras P03 (concept drift confirmado) e P04 (concept drift em atenção). Isso seguia a doutrina do projeto: rodar challenger em sombra é reversível, portanto automatizável.

O game day ([INC-0001](../incidents/0001-s2-concept-drift-dti.md), item de ação 2) mostrou que a marcação não correspondia ao sistema. O job registrava A6 entre as ações automáticas, mas nenhum código a executava, e o challenger do incidente foi treinado à mão. Uma matriz que declara ação automática inexistente engana quem está de plantão, que espera um challenger que nunca vem.

## Decisão

1. **A6 passa a ser ação humana** em P03 e P04. O job continua registrando a recomendação a cada lote (campo `human` da resposta, log e RUN record).
2. **Um comando documentado executa A6:**
   - **Comando:** `make gameday-shadow SCENARIO=<cenário> AT=<lote>`.
   - **Treino:** o challenger usa só o que é observável no lote escolhido, com as mesmas travas GR-7 (dado aprovado no contrato) e GR-8 (rótulo maduro).
   - **Sombra:** ele pontua os lotes seguintes sem decidir, com o gate GR-5 reavaliado a cada rótulo que amadurece.
   - **Recusa:** se as travas recusarem o treino, a recusa é a resposta e vai para o log.
3. **O playbook de `CDM_BAD_RATE_RATIO` e de `CDM_AUC_DROP` no [RUNBOOK](../RUNBOOK.md)** diz quando rodar o comando: no lote do alerta, com D3.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Implementar A6 no job | Fiel à doutrina; nenhum atraso humano | O job passa a guardar histórico de lotes, rótulos e modelos entre execuções; o treino entra no tempo de cada lote; nada consome o resultado automaticamente, porque promover (A7) é humano | Custo alto para uma ação cujo resultado só serve a uma decisão humana |
| Manter "auto" e documentar a lacuna | Nenhuma mudança | A matriz continua afirmando o que o sistema não faz | Pior que qualquer das duas outras opções |
| Disparar A6 por um orquestrador externo | Separa treino do job de monitoramento | Exige um orquestrador que o projeto não tem | Fora do escopo |

## Consequências

**Boas:**
- **A matriz descreve o que o sistema faz:** só A4 (modo conservador) é automático nas regras de concept drift.
- **O treino só acontece quando alguém vai olhar o resultado,** e no lote que a triagem escolheu.

**Ruins / custos aceitos:**
- **Diverge do princípio "sombra é automática" da doutrina.** A divergência fica registrada aqui.
- **O challenger depende de alguém rodar o comando.** No game day, isso aconteceu no mesmo lote do alerta, mas não há garantia de que aconteça.
- **Em sistema real, o comando teria de ler os lotes de produção,** não os de um cenário simulado.

## Como saberemos que a decisão estava errada

- **Challenger atrasado:** um incidente em que o challenger foi treinado lotes depois do alerta, com perda mensurável pelo atraso.
- **Infraestrutura nova:** o projeto ganha um armazenamento de histórico de lotes que torna barato treinar no job. Nesse caso, reabrir.

## Referências

- `config/response/policy.yaml` (P03, P04), `src/response/gameday.py` (`shadow_at`), `src/response/shadow.py`
- [INC-0001](../incidents/0001-s2-concept-drift-dti.md), [ADR-0013](0013-retraining-gate-rollback.md)
