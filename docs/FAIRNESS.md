# Análise de vieses

> Gerado por `make fairness` (`src/governance/report_doc.py`). Não editar à mão.

RUN: [RUN-20261117-fairness-ALL-01](runs/RUN-20261117-fairness-ALL-01.md). Grupos disponíveis no dado: `home_ownership`, faixas de `emp_length` e `addr_state` (não há gênero nem idade). "Aprovação dos bons" é a aprovação entre quem pagou (igualdade de oportunidade).

## Regime normal (teste de 2013, 16.177 propostas)

O champion aprova 99,8% das propostas no limiar da política. Gaps entre grupos com pelo menos 1000 propostas.


### `home_ownership`

Gap de aprovação 0,28% · gap de aprovação dos bons 0,22% · gap de calibração 0,03.

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| MORTGAGE | 8.665 | 99,9% | 100,0% | 99,7% | 14,1% | 1,01 | 0,714 |
| OWN | 1.335 | 99,9% | 99,9% | 99,5% | 16,6% | 1,03 | 0,692 |
| RENT | 6.177 | 99,7% | 99,8% | 99,2% | 17,4% | 1,00 | 0,678 |

### `emp_length`

Gap de aprovação 0,18% · gap de aprovação dos bons 0,21% · gap de calibração 0,10.

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| 0-1 | 1.110 | 99,7% | 99,8% | 99,4% | 16,0% | 1,04 | 0,687 |
| 1-5 | 4.265 | 99,8% | 99,8% | 99,7% | 15,6% | 1,02 | 0,693 |
| 10+ | 5.571 | 99,9% | 100,0% | 99,4% | 14,1% | 0,95 | 0,708 |
| 5-10 | 4.514 | 99,9% | 99,9% | 99,6% | 16,3% | 1,04 | 0,697 |
| desconhecido | 717 | 99,2% | 99,5% | 98,1% | 21,9% | 1,09 | 0,682 |

### `addr_state`

Gap de aprovação 0,21% · gap de aprovação dos bons 0,09% · gap de calibração 0,25.


## Força de proxy da região

Cramér's V entre `addr_state` (fora do modelo) e cada feature do modelo (numéricas em decis); 0 = nenhuma associação, 1 = a feature determina a região.

| Feature | Cramér's V |
|---|---|
| `home_ownership` | 0,193 |
| `tot_cur_bal` | 0,104 |
| `tot_hi_cred_lim` | 0,099 |
| `avg_cur_bal` | 0,090 |
| `mort_acc` | 0,084 |
| `annual_inc` | 0,053 |
| `dti` | 0,051 |
| `mths_since_recent_inq` | 0,047 |
| `total_acc` | 0,042 |
| `verification_status` | 0,040 |

## Modo conservador (fairness drift)

Gap médio por lote entre grupos com pelo menos 200 propostas no lote, e o máximo entre os lotes.


### S2 (do lote 8 em diante)

| Decisão | Valor vs. champion puro (US$ mil) | Gap `home_ownership` | Gap `emp_length` | Gap `addr_state` |
|---|---|---|---|---|
| champion puro | 0 | 0,3% (máx. 0,4%) | 0,5% (máx. 0,8%) | 0,4% (máx. 0,5%) |
| conservador sem limite | 2.942 | 13,1% (máx. 14,5%) | 40,8% (máx. 45,2%) | 7,1% (máx. 9,6%) |
| limite só em home_ownership | 2.868 | 7,0% (máx. 7,0%) | 37,4% (máx. 41,5%) | 6,3% (máx. 8,6%) |
| limite nos três segmentos | 2.738 | 6,8% (máx. 7,0%) | 6,8% (máx. 6,9%) | 6,2% (máx. 6,9%) |
| conservador com limite (política) | 2.737 | 6,8% (máx. 7,0%) | 6,8% (máx. 7,0%) | 6,3% (máx. 7,4%) |

Por grupo de `home_ownership`, conservador sem limite:

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| MORTGAGE | 12.811 | 87,9% | 89,9% | 79,9% | 19,7% | 1,41 | 0,730 |
| OWN | 2.081 | 81,5% | 84,0% | 71,9% | 21,2% | 1,35 | 0,716 |
| RENT | 9.097 | 74,8% | 79,6% | 58,8% | 23,0% | 1,33 | 0,712 |

Por grupo de `home_ownership`, conservador com limite (política):

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| MORTGAGE | 12.811 | 89,1% | 91,0% | 81,4% | 19,7% | 1,41 | 0,730 |
| OWN | 2.081 | 85,0% | 87,1% | 77,1% | 21,2% | 1,35 | 0,716 |
| RENT | 9.097 | 82,3% | 86,7% | 67,7% | 23,0% | 1,33 | 0,712 |

### S3 (do lote 7 em diante)

| Decisão | Valor vs. champion puro (US$ mil) | Gap `home_ownership` | Gap `emp_length` | Gap `addr_state` |
|---|---|---|---|---|
| champion puro | 0 | 0,3% (máx. 0,5%) | 0,9% (máx. 2,6%) | 0,5% (máx. 1,0%) |
| conservador sem limite | 2.662 | 19,3% (máx. 22,5%) | 42,3% (máx. 45,8%) | 8,2% (máx. 10,7%) |
| limite só em home_ownership | 2.604 | 7,0% (máx. 7,0%) | 38,2% (máx. 42,5%) | 9,4% (máx. 13,6%) |
| limite nos três segmentos | 2.477 | 7,0% (máx. 7,0%) | 6,8% (máx. 7,0%) | 5,8% (máx. 6,5%) |
| conservador com limite (política) | 2.544 | 7,0% (máx. 7,0%) | 6,8% (máx. 6,9%) | 8,1% (máx. 11,4%) |

Por grupo de `home_ownership`, conservador sem limite:

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| MORTGAGE | 16.099 | 81,4% | 83,5% | 73,3% | 21,0% | 1,51 | 0,696 |
| OWN | 2.595 | 70,4% | 74,2% | 57,9% | 23,7% | 1,48 | 0,693 |
| RENT | 11.295 | 62,1% | 66,1% | 50,0% | 25,0% | 1,43 | 0,686 |

Por grupo de `home_ownership`, conservador com limite (política):

| Grupo | Propostas | Aprovação | Aprovação dos bons | Aprovação dos maus | Bad rate | Calibração (obs/esp) | AUC |
|---|---|---|---|---|---|---|---|
| MORTGAGE | 16.099 | 82,7% | 84,9% | 74,5% | 21,0% | 1,51 | 0,696 |
| OWN | 2.595 | 77,8% | 81,2% | 67,0% | 23,7% | 1,48 | 0,693 |
| RENT | 11.295 | 75,8% | 80,0% | 63,2% | 25,0% | 1,43 | 0,686 |
