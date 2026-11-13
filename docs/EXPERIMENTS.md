# Experimentos de treino

> Gerado por `make report` (`src/reporting/experiments.py`) a partir do experimento MLflow
> `training`. Não editar à mão. Cada linha aponta para o RUN record que contém o mesmo run.

Legenda: CV = validação cruzada estratificada no train; test = 15% da referência 2013 nunca
vista no treino; OOT14/OOT15 = safras 2014/2015 maduras (fora do tempo); Brier pré/pós =
antes/depois da calibração; BR = bad rate esperado (média do score) e observado; PSI score =
estabilidade da distribuição do score (bins do test).

| RUN | Modelo | Calibração | AUC CV | AUC test | Gini test | KS test | PR-AUC test | Brier pré | Brier pós | AUC OOT14 | AUC OOT15 | BR esp. OOT15 | BR obs. OOT15 | PSI score OOT15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [RUN-20261113-train-REF-03](runs/RUN-20261113-train-REF-03.md) | xgboost | isotonic | 0.7009 | 0.6979 | 0.3957 | 0.2998 | 0.2822 | 0.1227 | 0.1229 | 0.6903 | 0.6928 | 0.1119 | 0.1488 | 0.2380 |
| [RUN-20261113-train-REF-02](runs/RUN-20261113-train-REF-02.md) | logreg **(champion)** | sigmoid | 0.6989 | 0.7001 | 0.4002 | 0.3032 | 0.2931 | 0.1225 | 0.1225 | 0.6907 | 0.6954 | 0.1156 | 0.1488 | 0.2257 |
| [RUN-20261113-train-REF-01](runs/RUN-20261113-train-REF-01.md) | dummy | none | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.1558 | 0.1316 | 0.1316 | 0.5000 | 0.5000 | 0.1560 | 0.1488 | 0.0000 |
| [RUN-20261112-train-REF-03](runs/RUN-20261112-train-REF-03.md) | xgboost | isotonic | 0.7009 | 0.6979 | 0.3957 | 0.2998 | 0.2822 | 0.1227 | 0.1229 | 0.6903 | 0.6928 | 0.1119 | 0.1488 | 0.2380 |
| [RUN-20261112-train-REF-02](runs/RUN-20261112-train-REF-02.md) | logreg | sigmoid | 0.6989 | 0.7001 | 0.4002 | 0.3032 | 0.2931 | 0.1225 | 0.1225 | 0.6907 | 0.6954 | 0.1156 | 0.1488 | 0.2257 |
| [RUN-20261112-train-REF-01](runs/RUN-20261112-train-REF-01.md) | dummy | none | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 0.1558 | 0.1316 | 0.1316 | 0.5000 | 0.5000 | 0.1560 | 0.1488 | 0.0000 |
