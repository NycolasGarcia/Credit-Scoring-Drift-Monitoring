# ADR-0005 — Separação referência × produção

- **Status:** aceito
- **Data:** 2026-11-12
- **Fase:** F1

## Contexto

O monitoramento compara a produção com uma **referência**: o que o modelo "conhecia" no treino. Se a referência for mal escolhida, todo drift medido fica contaminado. Os cenários simulados (F4) precisam de uma base sem drift própria, para que o drift medido seja só o injetado.

Restrições observadas na EDA:

- As features de bureau (`acc_open_past_24mths`, `bc_util`, `mort_acc`, `tot_*`…) são 100% nulas até 2011 e parciais em 2012 (14–52% de nulos). A partir de 2013 estão completas.
- A safra 2013 é 100% madura no snapshot (mar/2019), tanto para 36 quanto para 60 meses.

## Decisão

Configuração em `config/data/split.yaml`; lógica em `src/data/split.py`; execução por `make data`.

| Partição | Definição | Linhas | Uso |
|---|---|---|---|
| **reference** | Individual, safra 2013, madura e resolvida, 80% | 107.843 | Treino, validação e teste interno (F2) |
| **holdout** | Mesmo universo, 20% estratificado por mês de safra × alvo (seed 42) | 26.961 | Base dos cenários simulados S0–S4 (F4) |
| **production** | Individual, safras jan/2014–dez/2018, todos os status | 1.909.242 | Produção natural S5: lotes mensais, drift real, rótulo com atraso |
| **out_of_scope** | Joint, safras 2007–2012, 2013 não resolvido | 216.622 | Não persistido |

Contagens em `docs/evidence/data/split_manifest.json`, com hash de conteúdo por partição e sha256 do arquivo bruto.

Garantias testadas (`tests/test_target_split.py`): interseção de ids entre partições = 0; referência e holdout só da janela, maduros e rotulados; produção só a partir do início configurado; partição determinística para a mesma seed.

O identificador original é substituído por `loan_key` (HMAC-SHA256 com chave do `.env`) antes da persistência. Os hashes de conteúdo dependem dessa chave: são reprodutíveis com a mesma chave e o mesmo arquivo bruto.

## Alternativas consideradas

| Alternativa | Prós | Contras | Por que não |
|---|---|---|---|
| Referência 2012–2013 | Mais volume | Bureau 52% nulo em 2012, o que gera drift estrutural de nulos | Contamina o PSI |
| Split aleatório sem tempo | Simples | Mistura épocas; nenhum drift real a observar | Contraria o RO-7 |
| Holdout de outra safra | Testa generalização temporal | O cenário simulado deixa de medir só o drift injetado | O OOT temporal já é feito na F2 sobre a produção madura |
| Incluir Joint com features nulas | Mais volume | Schema diferente e inexistente na referência | Escopo do modelo é individual |

## Consequências

**Boas:** a referência é homogênea e madura; os cenários simulados partem de uma base A/A; a produção natural tem 60 lotes mensais com drift real.

**Ruins / custos aceitos:** só 12 meses de referência, com a sazonalidade de um único ano. O OOT na F2 usa as safras de produção já maduras (2014 e 36 meses de 2015–2016), uma amostra parcial.

## Como saberemos que a decisão estava errada

O cenário de controle S0 (lotes do holdout) disparar drift acima do alvo de falso alarme na F5. Isso indicaria uma referência heterogênea demais ou um holdout não representativo.
