# ADR-0017 — Desenho do simulador de cenários de degradação

- **Status:** aceito
- **Data:** 2026-11-13
- **Fase:** F4

## Contexto

O detector de drift (F5) e a política de resposta (F7) precisam ser **avaliados**, não só demonstrados. Avaliar exige ground truth: saber o que mudou, onde, quando e quanto. A produção natural (2014–2018) tem drift real, mas sem verdade conhecida e com rótulo censurado nas safras finais (NV-7, ADR-0004). Por isso, a maior parte dos cenários é sintetizada a partir do **holdout de 2013** (ADR-0005), que é a mesma população da referência e nunca foi usado no treino.

Forças:
- O drift medido precisa ser **só o injetado**: a base dos cenários não pode carregar drift próprio.
- **Coerência dos rótulos:** se X muda, o rótulo precisa mudar de forma coerente; caso contrário, o "choque econômico" não aumentaria a inadimplência.
- **Contrato:** cada lote passa pelo contrato da F3. Um cenário que viole regras por descuido (por exemplo, juros alterados sem recalcular a parcela) mediria o contrato, não o drift.
- **Determinismo:** mesma seed → mesmo hash, e cada lote reproduzível isoladamente.

## Decisão

1. **Base e amostragem.** Os cenários S0–S4 têm 12 lotes mensais de 6.000 propostas cada. As propostas são amostradas sem reposição dentro do lote a partir do holdout (26.961 linhas). Cada lote usa um gerador próprio, semeado por `(seed do cenário, índice do lote)`. As chaves são sintéticas (`S1-03-00042`), e as datas seguem um calendário simulado a partir de 2014-01.
2. **Três famílias de transformação**, aplicadas nesta ordem:
   - **mundo real** (`scale`, `shift`): a população muda. A parcela é recalculada pela amortização sempre que juros, valor ou prazo mudam;
   - **bug de dado** (`unit_bug`): só o dado observado muda, a realidade (e o rótulo) não;
   - **mecanismo do rótulo** (`logit_shift`): P(default | X) muda por um deslocamento conhecido no logit, global ou num segmento definido por um decil da referência, e X fica intacto.
3. **Rótulos por oráculo.** A P(default | X) da referência é estimada pelo champion calibrado (|esperado − observado| = 0,08 p.p. no teste, [RUN-20261113-train-REF-02](../runs/RUN-20261113-train-REF-02.md)). Cada rótulo real é movido do risco `p_old` (X original) para o risco `p_new` (X transformado e logit deslocado) por um sorteio que garante E[y_new | x] = p_new. Quando o risco não muda, o desfecho real é mantido intacto. Consequência: em S1 (D1) o modelo continua calibrado, ou seja, há drift **sem** degradação, e S2/S3 degradam por construção.
4. **Atraso de rótulo comprimido.** Nos cenários simulados, o rótulo de um lote fica observável `label_lag = 3` lotes depois. É um proxy, como a inadimplência de 90+ dias, e não os 36 meses reais. Em S5, o atraso é o real: o rótulo fica disponível no mês de vencimento e só para contratos maduros no snapshot.
5. **S4 parcial.** O bug de unidade atinge 30% das linhas. Com 100%, o lote seria bloqueado pela regra H10 do contrato, como a varredura D6 da F3 mostrou. A 30% o bug escapa do contrato, e cabe à F5 reconhecê-lo como D6.
6. **Pontuação pelo gate.** Todos os lotes passam pelo quality gate da F3 e são pontuados pelo champion, como em produção. Cada cenário gera um manifesto de ground truth com agregados e hashes, persistido em `docs/evidence/scenarios/`, e um RUN record do tipo `sim`.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Só produção natural (S5) | Drift 100% real | Sem ground truth; rótulo censurado a partir de 2016 | Não permite medir recall, falso alarme nem atraso de detecção |
| Dados sintéticos do zero (gerador paramétrico) | Controle total | Distribuições conjuntas irreais; o modelo seria avaliado num mundo que ele nunca viu | Perde a ancoragem no dado real |
| Manter o rótulo real em S1 (sem oráculo) | Simples; não depende do modelo | Renda menor sem mais inadimplência: o choque econômico não teria consequência e o "drift" viraria ruído | Contradiz o mecanismo que o cenário quer representar |
| Sortear rótulos novos de `p_new` para todas as linhas | Simples | Descarta o desfecho real mesmo quando nada mudou; S0 deixaria de ser A/A sobre o dado real | O sorteio condicional preserva o real e só altera o necessário |
| Oráculo independente (outro modelo, ex.: XGBoost) | Evita a circularidade "o modelo julga a si mesmo" | O XGBoost não é melhor calibrado (Brier 0,1229 contra 0,1225 do champion no teste, [RUN-20261113-train-REF-03](../runs/RUN-20261113-train-REF-03.md) × [REF-02](../runs/RUN-20261113-train-REF-02.md)); adiciona uma segunda fonte de erro | A circularidade é explicitada e só afeta S1; S2/S3 deslocam o logit de forma conhecida |
| Bug de unidade em 100% das linhas | Fiel ao defeito clássico | Bloqueado pelo contrato; nada a avaliar na F5 | Já demonstrado na F3 (`validate-bad`) |

## Consequências

**Boas:**
- Cada cenário tem uma resposta certa declarada (`expected.layers`, `expected.diagnosis`), e a F5 pode tratar o detector como um classificador.
- S1 e S2 separam limpamente D1 de D3: em S1, X e score mudam e o desempenho se mantém; em S2, nada muda nas entradas e só o desempenho com rótulo revela o problema.
- Os cenários são reproduzíveis e auditáveis: config com hash, base com hash, hash por lote e RUN record.

**Ruins / custos aceitos:**
- **Circularidade em S1:** "drift sem degradação" é verdadeiro por construção, assumindo que o champion é a P(Y|X) real. Em dado real, um choque econômico pode trazer concept drift junto; esse caso é coberto por S2.
- O rótulo comprimido (3 lotes) subestima o atraso real, o que torna o detection delay de L4 otimista. O RUN de S5 mostra o atraso real.
- A amostragem sem reposição dentro do lote repete propostas entre lotes, então os lotes não são independentes. Isso torna o S0 um pouco "fácil demais"; a calibração de limiares na F5 deve usar bootstrap.

## Como saberemos que a decisão estava errada

- **S0 alarma** (PSI > 0,10 ou SEV-2+) numa fração relevante dos lotes **sem drift injetado**: a amostragem estaria introduzindo diferenças, e o S0 deixaria de servir como controle.
- **Em S1, o bad rate observado diverge do esperado** (média de `p_oracle`) além do ruído amostral: o mecanismo de rótulo não estaria preservando P(Y|X).
- **A F5 não consegue separar S1 de S2,** ou separa por artefato do simulador (por exemplo, pela chave ou pela data) e não pelo sinal.

## Referências

- `config/scenarios/S0.yaml` … `S5.yaml`; `src/simulation/` (engine, transforms, labels, natural, manifest, record)
- [SCENARIOS.md](../SCENARIOS.md) — narrativa econômica e resultados
- [ADR-0004](0004-target-maturity-leakage.md) (maturação), [ADR-0005](0005-reference-production-split.md) (holdout), [ADR-0008](0008-data-contracts.md) (gate)
- `docs/evidence/contracts/d6_sweep.json` (por que S4 é parcial)
