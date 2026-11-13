# Inventário de colunas

> Gerado por `python -m src.data.inventory` a partir de `config/data/column_inventory.yaml`.
> Não editar à mão: altere o YAML e regenere.

Legenda — **cat**: categoria do dado · **pii**: dado pessoal (LGPD) direto,
quase-identificador ou não · **use**: destino no projeto.
Nenhuma coluna é dado pessoal *sensível* (LGPD art. 5º, II).

**Total: 151 colunas** — alvo: 1 · chave: 1 · descartado: 114 · feature: 32 · metadado: 2 · segmento: 1

| Coluna | cat | pii | use | Racional |
|---|---|---|---|---|
| `id` | identificador_direto | direto | chave | pseudonimizado via HMAC; valor original nunca sai do loader |
| `member_id` | identificador_direto | direto | descartado | 100% nulo no arquivo |
| `url` | identificador_direto | direto | descartado | contém o id |
| `emp_title` | texto_livre | quase | descartado | texto livre do tomador; minimização |
| `desc` | texto_livre | quase | descartado | texto livre do tomador; minimização |
| `title` | texto_livre | quase | descartado | texto livre do tomador; minimização |
| `zip_code` | quase_identificador | quase | descartado | 3 dígitos de CEP; minimização (região coberta por addr_state) |
| `addr_state` | quase_identificador | quase | segmento | fora do modelo (proxy regional); usado só em fairness e monitoramento |
| `earliest_cr_line` | quase_identificador | quase | descartado | data bruta substituída pela derivada credit_history_months |
| `loan_status` | alvo | nao | alvo |  |
| `issue_d` | metadado | nao | metadado | safra; eixo temporal da separação |
| `application_type` | metadado | nao | metadado | escopo = Individual; Joint só existe a partir de 2015-12 |
| `policy_code` | metadado | nao | descartado | constante |
| `initial_list_status` | originacao | nao | descartado | canal de investidor, não atributo do tomador |
| `disbursement_method` | originacao | nao | descartado | só existe a partir de 2018 |
| `funded_amnt` | originacao | nao | descartado | redundante com loan_amnt |
| `funded_amnt_inv` | originacao | nao | descartado | processo de funding por investidores; fora da aba browseNotes |
| `loan_amnt` | originacao | nao | feature |  |
| `term` | originacao | nao | feature |  |
| `int_rate` | originacao | nao | feature |  |
| `installment` | originacao | nao | feature |  |
| `grade` | originacao | nao | feature |  |
| `emp_length` | originacao | quase | feature | também segmento de fairness |
| `home_ownership` | originacao | quase | feature | também segmento de fairness |
| `annual_inc` | originacao | quase | feature |  |
| `verification_status` | originacao | nao | feature |  |
| `purpose` | originacao | nao | feature |  |
| `dti` | originacao | nao | feature |  |
| `delinq_2yrs` | originacao | nao | feature |  |
| `fico_range_low` | originacao | quase | feature |  |
| `inq_last_6mths` | originacao | nao | feature |  |
| `mths_since_last_delinq` | originacao | nao | feature | nulo = nunca inadimpliu |
| `open_acc` | originacao | nao | feature |  |
| `pub_rec` | originacao | nao | feature |  |
| `revol_bal` | originacao | nao | feature |  |
| `revol_util` | originacao | nao | feature |  |
| `total_acc` | originacao | nao | feature |  |
| `mort_acc` | originacao | nao | feature |  |
| `pub_rec_bankruptcies` | originacao | nao | feature |  |
| `acc_open_past_24mths` | originacao | nao | feature |  |
| `bc_util` | originacao | nao | feature |  |
| `avg_cur_bal` | originacao | nao | feature |  |
| `tot_hi_cred_lim` | originacao | nao | feature |  |
| `num_actv_rev_tl` | originacao | nao | feature |  |
| `percent_bc_gt_75` | originacao | nao | feature |  |
| `mths_since_recent_inq` | originacao | nao | feature |  |
| `mo_sin_old_rev_tl_op` | originacao | nao | feature |  |
| `tot_cur_bal` | originacao | nao | feature |  |
| `total_bc_limit` | originacao | nao | feature |  |
| `sub_grade` | originacao | nao | descartado | redundante com grade e int_rate |
| `fico_range_high` | originacao | quase | descartado | fico_range_low + 4 |
| `mths_since_last_record` | originacao | nao | descartado | ~88% nulo em 2013 |
| `mths_since_last_major_derog` | originacao | nao | descartado | ~80% nulo em 2013 |
| `collections_12_mths_ex_med` | originacao | nao | descartado | quase constante |
| `acc_now_delinq` | originacao | nao | descartado | quase constante |
| `chargeoff_within_12_mths` | originacao | nao | descartado | quase constante |
| `delinq_amnt` | originacao | nao | descartado | quase constante |
| `tax_liens` | originacao | nao | descartado | quase constante |
| `num_tl_120dpd_2m` | originacao | nao | descartado | dicionário: 'updated in past 2 months' (ambíguo) e quase constante |
| `num_tl_30dpd` | originacao | nao | descartado | dicionário: 'updated in past 2 months' (ambíguo) e quase constante |
| `bc_open_to_buy` | originacao | nao | descartado | redundância com total_bc_limit e bc_util |
| `mo_sin_old_il_acct` | originacao | nao | descartado | parcimônia |
| `mo_sin_rcnt_rev_tl_op` | originacao | nao | descartado | parcimônia |
| `mo_sin_rcnt_tl` | originacao | nao | descartado | parcimônia |
| `mths_since_recent_bc` | originacao | nao | descartado | parcimônia |
| `mths_since_recent_bc_dlq` | originacao | nao | descartado | ~78% nulo |
| `mths_since_recent_revol_delinq` | originacao | nao | descartado | ~70% nulo |
| `num_accts_ever_120_pd` | originacao | nao | descartado | parcimônia |
| `num_actv_bc_tl` | originacao | nao | descartado | redundância com num_actv_rev_tl |
| `num_bc_sats` | originacao | nao | descartado | parcimônia |
| `num_bc_tl` | originacao | nao | descartado | parcimônia |
| `num_il_tl` | originacao | nao | descartado | parcimônia |
| `num_op_rev_tl` | originacao | nao | descartado | redundância com open_acc |
| `num_rev_accts` | originacao | nao | descartado | redundância com total_acc |
| `num_rev_tl_bal_gt_0` | originacao | nao | descartado | parcimônia |
| `num_sats` | originacao | nao | descartado | redundância com open_acc |
| `num_tl_90g_dpd_24m` | originacao | nao | descartado | quase constante |
| `num_tl_op_past_12m` | originacao | nao | descartado | redundância com acc_open_past_24mths |
| `pct_tl_nvr_dlq` | originacao | nao | descartado | parcimônia |
| `total_bal_ex_mort` | originacao | nao | descartado | redundância com tot_cur_bal |
| `total_il_high_credit_limit` | originacao | nao | descartado | parcimônia |
| `tot_coll_amt` | originacao | nao | descartado | quase constante |
| `total_rev_hi_lim` | originacao | nao | descartado | redundância com tot_hi_cred_lim |
| `open_acc_6m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `open_act_il` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `open_il_12m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `open_il_24m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `mths_since_rcnt_il` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `total_bal_il` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `il_util` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `open_rv_12m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `open_rv_24m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `max_bal_bc` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `all_util` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `inq_fi` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `total_cu_tl` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `inq_last_12m` | originacao | nao | descartado | 100% nulo na referência 2013 |
| `annual_inc_joint` | originacao | quase | descartado | escopo Individual |
| `dti_joint` | originacao | nao | descartado | escopo Individual |
| `verification_status_joint` | originacao | nao | descartado | escopo Individual |
| `revol_bal_joint` | originacao | nao | descartado | escopo Individual |
| `sec_app_fico_range_low` | originacao | quase | descartado | escopo Individual |
| `sec_app_fico_range_high` | originacao | quase | descartado | escopo Individual |
| `sec_app_earliest_cr_line` | quase_identificador | quase | descartado | escopo Individual |
| `sec_app_inq_last_6mths` | originacao | nao | descartado | escopo Individual |
| `sec_app_mort_acc` | originacao | nao | descartado | escopo Individual |
| `sec_app_open_acc` | originacao | nao | descartado | escopo Individual |
| `sec_app_revol_util` | originacao | nao | descartado | escopo Individual |
| `sec_app_open_act_il` | originacao | nao | descartado | escopo Individual |
| `sec_app_num_rev_accts` | originacao | nao | descartado | escopo Individual |
| `sec_app_chargeoff_within_12_mths` | originacao | nao | descartado | escopo Individual |
| `sec_app_collections_12_mths_ex_med` | originacao | nao | descartado | escopo Individual |
| `sec_app_mths_since_last_major_derog` | originacao | nao | descartado | escopo Individual |
| `pymnt_plan` | pos_originacao | nao | descartado |  |
| `out_prncp` | pos_originacao | nao | descartado |  |
| `out_prncp_inv` | pos_originacao | nao | descartado |  |
| `total_pymnt` | pos_originacao | nao | descartado |  |
| `total_pymnt_inv` | pos_originacao | nao | descartado |  |
| `total_rec_prncp` | pos_originacao | nao | descartado |  |
| `total_rec_int` | pos_originacao | nao | descartado |  |
| `total_rec_late_fee` | pos_originacao | nao | descartado |  |
| `recoveries` | pos_originacao | nao | descartado |  |
| `collection_recovery_fee` | pos_originacao | nao | descartado |  |
| `last_pymnt_d` | pos_originacao | nao | descartado | lido só para datar o snapshot |
| `last_pymnt_amnt` | pos_originacao | nao | descartado |  |
| `next_pymnt_d` | pos_originacao | nao | descartado |  |
| `last_credit_pull_d` | pos_originacao | nao | descartado |  |
| `last_fico_range_high` | pos_originacao | quase | descartado |  |
| `last_fico_range_low` | pos_originacao | quase | descartado |  |
| `hardship_flag` | pos_originacao | nao | descartado |  |
| `hardship_type` | pos_originacao | nao | descartado |  |
| `hardship_reason` | pos_originacao | quase | descartado |  |
| `hardship_status` | pos_originacao | nao | descartado |  |
| `deferral_term` | pos_originacao | nao | descartado |  |
| `hardship_amount` | pos_originacao | nao | descartado |  |
| `hardship_start_date` | pos_originacao | nao | descartado |  |
| `hardship_end_date` | pos_originacao | nao | descartado |  |
| `payment_plan_start_date` | pos_originacao | nao | descartado |  |
| `hardship_length` | pos_originacao | nao | descartado |  |
| `hardship_dpd` | pos_originacao | nao | descartado |  |
| `hardship_loan_status` | pos_originacao | nao | descartado |  |
| `orig_projected_additional_accrued_interest` | pos_originacao | nao | descartado |  |
| `hardship_payoff_balance_amount` | pos_originacao | nao | descartado |  |
| `hardship_last_payment_amount` | pos_originacao | nao | descartado |  |
| `debt_settlement_flag` | pos_originacao | nao | descartado |  |
| `debt_settlement_flag_date` | pos_originacao | nao | descartado |  |
| `settlement_status` | pos_originacao | nao | descartado |  |
| `settlement_date` | pos_originacao | nao | descartado |  |
| `settlement_amount` | pos_originacao | nao | descartado |  |
| `settlement_percentage` | pos_originacao | nao | descartado |  |
| `settlement_term` | pos_originacao | nao | descartado |  |
