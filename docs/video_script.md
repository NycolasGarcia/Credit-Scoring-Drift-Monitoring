# Roteiro do vídeo (STAR, ≤ 5:00)

Tempo-alvo: **4:40**, com 20 s de folga. Cada bloco diz o que mostrar na tela e o que falar. Os números citados são os do README, cada um com o RUN que o produziu.

**Preparação antes de gravar**
1. `make stack-up` e um `make replay SCENARIO=S2 INTERVAL=5` já executado, para o dashboard ter dados.
2. Abas abertas: README, dashboard do Grafana (cenário S2), `docs/evidence/drift/S1_evidently.html`, `docs/evidence/contracts/bad-all-seed7.json`, `docs/RESPONSE_EVALUATION.md`, `docs/incidents/0001-s2-concept-drift-dti.md`, `docs/FAIRNESS.md`.
3. Terminal na raiz do projeto, com fonte grande.

## S — Situação (0:00–0:40)

**Tela:** README, primeiro parágrafo e o diagrama de arquitetura.

**Fala:**
> Uma fintech tem um modelo de crédito em produção. A economia mudou: inflação, juros, desemprego. A diretoria desconfia que o modelo está errando, mas nenhum painel mostra isso. Esse é o risco da degradação silenciosa: o rótulo de inadimplência só chega meses depois, e até lá o modelo continua aprovando quem não vai pagar. Este projeto é acadêmico; a produção é simulada com lotes mensais do Lending Club, de 2014 a 2018, mais seis cenários com o que muda conhecido de antemão.

## T — Tarefa (0:40–1:20)

**Tela:** README, tabela de resultados (só os títulos das linhas).

**Fala:**
> A tarefa tem três partes. Primeiro, impedir que dado ruim chegue ao modelo. Segundo, detectar drift e, mais difícil, saber se o drift virou degradação, e de que tipo. Terceiro, decidir o que fazer, com custo medido e dentro da LGPD. Detectar é metade; a outra metade é responder sem piorar as coisas.

## A — Ação (1:20–3:20)

**1. Contrato de dados (1:20–1:50)**

**Tela:** terminal com `make validate-bad`, depois o JSON da evidência.

> Um lote com treze defeitos catalogados (renda negativa, coluna extra, renda mensal no lugar de anual) passa pelo contrato em Pandera. Resultado: lote bloqueado, zero linhas pontuadas, quarentena com relatório só de agregados.

**2. Simulação e detecção (1:50–2:30)**

**Tela:** relatório Evidently do S1 (variáveis em drift); depois a tabela-resumo do DRIFT_EVALUATION.

> O simulador cria lotes com degradação controlada. No choque econômico, o detector aponta as três variáveis alteradas (renda, DTI e juros) com PSI calculado sobre faixas fixas da referência, e o Evidently confirma. O ponto é o diagnóstico: no choque, o modelo continua calibrado, é drift sem degradação. No concept drift, as entradas não mudam nada; só o desempenho com rótulo maduro revela o problema. O detector separa os dois casos e nunca alarmou no cenário de controle.

**3. Observabilidade (2:30–2:55)**

**Tela:** dashboard do Grafana no S2: painéis de desempenho maduro, alertas e resposta.

> Cada lote passa por oito etapas, com log estruturado e métricas no Prometheus. Doze alertas, cada um com playbook. Aqui o alerta de bad rate acima do esperado dispara em SEV-2 no lote 8.

**4. Resposta e governança (2:55–3:20)**

**Tela:** `config/response/policy.yaml` (regra P03), depois o GOVERNANCE.md (aviso de escopo e tabela de códigos de motivo).

> A resposta é uma matriz declarativa: o diagnóstico decide a ação. Concept drift confirmado liga o modo conservador, que retém as propostas de valor esperado negativo com o risco corrigido, e cada decisão sai com um código de motivo, o que sustenta a revisão de decisão automatizada da LGPD. Promover um modelo novo é sempre decisão humana, com gate e rollback em um comando.

## R — Resultado (3:20–4:40)

**1. Drift apontado e alerta (3:20–3:40)**

**Tela:** INC-0001, linha do tempo.

> No game day, operei o cenário sem olhar o gabarito. O alerta disparou, o modo conservador entrou sozinho no mesmo lote, e o diagnóstico (concept drift no segmento de DTI alto) bateu com o gabarito.

**2. Guardrail agindo e impacto (3:40–4:05)**

**Tela:** RESPONSE_EVALUATION.md, tabela do S2; depois a linha do S4 com o modo conservador forçado.

> Em cinco seeds novos, o modo conservador rendeu, em mediana, 2,1 milhões de dólares contra não fazer nada no concept drift e 2,2 milhões no prior shift. E o guardrail certo importa: forçar o mesmo modo sobre um bug de dado perderia mais de 6 milhões. Por isso bug vai para quarentena, nunca para retreino.

**3. Lições aprendidas (4:05–4:40)**

**Tela:** README, seção "Lições" e a tabela do FAIRNESS.md.

> Três lições. Drift não é degradação: é preciso olhar o desempenho, e ele chega atrasado. Retreinar não é a resposta padrão: sobre um bug, o retreino parece dar lucro e esconde o defeito. E a própria resposta pode discriminar: o modo conservador cortava cerca de 40 pontos a mais de quem não informou o emprego. Limitar essa diferença custou só 4 a 7% do ganho. Tudo está documentado, com cada número ligado à execução que o produziu.

## Checklist do critério

| Exigência | Onde aparece |
|---|---|
| S: risco da degradação silenciosa | 0:00–0:40 |
| T: interceptar dado ruim, detectar drift, compliance | 0:40–1:20 |
| A: ferramentas, simulação, plano de governança | 1:20–3:20 |
| R: relatório apontando drift | 1:50 (Evidently) e 3:20 |
| R: alertas gerados | 2:30 e 3:20 |
| R: guardrail agindo e impacto | 3:40 |
| R: lições aprendidas | 4:05 |
