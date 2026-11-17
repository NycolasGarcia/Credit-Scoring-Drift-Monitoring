# ADR-0014 — Dados pessoais, base legal e retenção

- **Status:** aceito (prazos PROPOSTO em `config/governance/retention.yaml`)
- **Data:** 2026-11-17
- **Fase:** F8

> **Escopo acadêmico.** Este projeto é um trabalho acadêmico. Não existe fintech, cliente, titular atendido nem modelo em produção. O plano para a fintech descreve como a governança funcionaria **se** este modelo estivesse em produção, como exercício pedido pelo enunciado. Não é parecer jurídico, não foi revisado por profissional do direito e não deve ser usado como orientação legal. As citações legais foram conferidas no texto vigente publicado pelo Planalto em 2026-11-17.

## Contexto

O critério de governança pede clareza sobre privacidade, base legal e retenção. Há duas situações diferentes, e misturá-las faria o projeto afirmar o que não é:

1. **O projeto real.**
   - **Dados:** o dataset público do Lending Club (licença CC0), com empréstimos de pessoas reais nos Estados Unidos, sem nome, mas com quase-identificadores (3 dígitos do CEP, estado, renda, cargo em texto livre).
   - **Âmbito:** o processamento acontece no Brasil, então está no âmbito territorial da LGPD (art. 3º, I).
   - **Exceção acadêmica:** a finalidade é exclusivamente acadêmica, o que afasta a lei, salvo os arts. 7º e 11 (art. 4º, II, "b").
2. **O cenário do enunciado.** Uma fintech que concede crédito a pessoas no Brasil, à qual a LGPD se aplica integralmente (art. 3º, II).

## Decisão

1. **Situação real do projeto, declarada como tal.**
   - **Enquadramento:** tratamento para fins exclusivamente acadêmicos (art. 4º, II, "b").
   - **Base legal (o art. 7º continua valendo):** dado de acesso público, usado com respeito à finalidade e à boa-fé da disponibilização (art. 7º, §3º) e numa nova finalidade legítima, preservados os princípios (art. 7º, §7º).
   - **Dado tratado como pseudonimizado, não como anônimo** (art. 12): id substituído por HMAC com chave fora do repositório; texto livre, CEP e data bruta descartados; nada de linha de dado versionado; logs e relatórios só com agregados (GR-10).
2. **Plano para a fintech, como exercício acadêmico.**
   - **Base legal da decisão de crédito:** proteção do crédito (art. 7º, X).
   - **Direitos do titular:** art. 18.
   - **Revisão de decisão automatizada:** art. 20 da LGPD e art. 5º, VI da Lei 12.414/2011, ligada à fila do modo conservador e aos códigos de motivo.
   - **Registro e RIPD:** arts. 37 e 38.
   - **Retenção** pelos prazos de `config/governance/retention.yaml`: proposta e decisão por contrato + 5 anos, partições de treino e modelos pela vida útil + 5 anos, quarentena por 90 dias, logs por 1 ano, agregados sem prazo.
3. **Retenção executável onde há dado real.** `make retention` expurga, por idade, a quarentena e os logs locais; por padrão só simula, e `APPLY=1` apaga. Um teste garante que todo item de retenção aparece no plano.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Tratar o dataset como anônimo e declarar a LGPD inaplicável | Simples | Quase-identificadores tornam a reidentificação plausível (art. 12) | Postura menos prudente do que o próprio pipeline já pratica |
| Escrever só o plano da fintech, sem separar a situação real | Atende a rubrica | Dá a entender que o projeto cumpre obrigações que não tem, ou que há operação real | Enganoso |
| Prazos mais curtos (decisão = contrato + 2 anos, quarentena 30 dias) | Menos exposição | Menos capacidade de responder a contestação e auditoria tardias | Prazos do CDC art. 43 §1º usados como referência |
| Retenção só documental, sem mecanismo | Menos código | Prazo sem expurgo é declaração de intenção | O que existe localmente tem expurgo real |

## Consequências

**Boas:**
- **Leitura sem ambiguidade:** quem lê sabe o que vale para o TCC e o que é plano do cenário.
- **Citações verificáveis:** todas foram conferidas no texto vigente (NV-11 fechado).
- **Retenção que roda:** a parte com dado real tem expurgo testado.

**Ruins / custos aceitos:**
- **Prazos são premissa do autor** (PROPOSTO), não exigência legal medida.
- **O enquadramento acadêmico é leitura do texto legal,** não parecer.
- **Linhas brutas na quarentena:** ela guarda as linhas inválidas com os valores brutos (ressalva do Pandera no ADR-0008), e por isso tem o prazo mais curto.

## Como saberemos que a decisão estava errada

- **Uso fora do âmbito acadêmico:** o projeto passa a ser usado para decidir crédito de verdade. Nesse caso, o plano precisa de revisão jurídica antes de qualquer uso.
- **Lei alterada:** mudança nos artigos citados (rever no Planalto).
- **Quarentena mais velha que o prazo:** a quarentena acumula arquivos acima de 90 dias, o que indica que o expurgo não está sendo executado.

## Referências

- [GOVERNANCE.md](../GOVERNANCE.md), `config/governance/retention.yaml`, `src/governance/retention.py`, [data_inventory.md](../data_inventory.md)
- LGPD (Lei 13.709/2018): arts. 3º, 4º, 5º, 6º, 7º, 12, 16, 18, 20, 37, 38 · CDC (Lei 8.078/1990): art. 43 · Lei 12.414/2011: arts. 5º e 14
