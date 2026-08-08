# oskill Skills Index

## Group 1: Performance Evaluation

| Skill | Description | Calls |
|-------|-------------|-------|
| `bootstrap_sharpe` | Sharpe ratio bootstrap distribution + CI | `bootstrap_ci`, `sharpe_ratio` |
| `psr_dsr` | Probabilistic & Deflated Sharpe Ratio | `bootstrap_ci`, `skew_kurt_robust`, `sharpe_ratio` |
| `factor_attribution` | Fama-French factor attribution + bootstrap CI | `beta_alpha_ols`, `bootstrap_ci` |
| `regime_aware_performance` | Per-regime performance breakdown | `regime_filter_data`, `sharpe_ratio`, `drawdown_curve`, `value_at_risk` |

## Group 2: Time-Series Validation

| Skill | Description | Calls |
|-------|-------------|-------|
| `walk_forward_optimization` | Walk-Forward IS/OOS rolling splits | `purge_embargo_split`, `rolling_window_split` |
| `cpcv_pipeline` | Combinatorial Purged CV with path reconstruction | `purge_embargo_split`, `bootstrap_ci`, `distribution_summary` |
| `regime_aware_rolling` | Regime-aware rolling window computation | `regime_filter_data`, `rolling_window_split` |

## Group 3: Distribution & Anomaly

| Skill | Description | Calls |
|-------|-------------|-------|
| `distribution_shift_test` | Multi-method distribution drift detection | `kolmogorov_smirnov_test`, `wasserstein_distance`, `symmetric_kl_divergence`, `distribution_summary` |
| `detect_outliers_robust` | Robust multi-method outlier detection | `zscore_normalize`, `distribution_summary` |
| `bootstrap_distribution` | Bootstrap distribution of any statistic | `bootstrap_ci`, `distribution_summary`, `kde_density` |

## Group 4: Similarity Retrieval

| Skill | Description | Calls |
|-------|-------------|-------|
| `historical_analogy_search` | Historical analogy ensemble search | `dtw_distance`, `wasserstein_distance`, `cosine_similarity_batch`, `euclidean_distance_matrix` |
| `regime_transition_analysis` | Regime transition matrix + duration analysis | `regime_transition_matrix`, `regime_filter_data`, `distribution_summary` |
| `commodity_ratio_analytics` | Commodity price ratio analysis + regime classification | `percentile_rank`, `zscore_normalize` |
| `geopolitical_risk_index` | Geopolitical risk index from event data with EWMA decay | `ewma_smooth`, `percentile_rank` |

## Group 5: Prediction Quality

| Skill | Description | Calls |
|-------|-------------|-------|
| `calibration_analysis` | Full calibration analysis (Brier + ECE + MCE) | `brier_score_decomposed`, `percentile_rank`, `bayes_beta_update` |

## Group 6: General Purpose (MathModelAgent SKILL 3O 内化, v4.15.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `typst_minimal_doc` | Typst 最小文档生成 | — |
| `typst_format_check` | typstyle 格式化检查循环 (check→diff→apply) | `bash_exec` |
| `typst_probe` | 无文件 Typst 表达式探针 (stdin + query) | `bash_exec` |
| `typst_compile` | typst compile 编译验证 | `bash_exec` |
| `detect_platform` | 平台/发行版/包管理器检测 | `bash_exec` |
| `check_dependencies` | 依赖探测 (cmd / python 包) | `bash_exec`, `_import_module` |
| `install_commands` | 按平台选择安装命令 | — |
| `run_doctor` | 环境检查总入口 (可选自动安装) | 上述全部 |
| `resolve_template` | 科研绘图模板解析 (id/别名/中文) | — |
| `list_figure_templates` | 模板清单 | — |
| `render_figure_template` | 复制模板脚本到工作区并执行 | `subprocess` |
| `drawio_node` / `drawio_edge` | DrawIO 节点/边描述 | — |
| `drawio_doc` | 由节点/边生成 mxfile XML | — |
| `export_drawio` | drawio CLI 导出 PDF (自动探测二进制) | `bash_exec` |
| `validate_drawio` | .drawio 自检 (良构/节点/悬空边) | — |
| `render_drawio` | 生成→写入→自检→导出 一站式 | 上述全部 |
| `resolve_config` | 验收路径推断 (main/sections/figures...) | — |
| `run_text_gate` | 文本质量门禁 (结构/标题/占位符/泄露/图表/数值) | `bash_exec` |
| `compile_paper` | typst / xelatex×2 编译 | `bash_exec` |
| `pdf_pages` | PDF 栅格化为 PNG (pdftoppm/mutool/magick) | `bash_exec` |
| `run_verity` | 验收总入口 (门禁+编译+栅格化) | 上述全部 |

## Group 7: Engineering Workflow (mattpocock skills 3O 内化, v4.17.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `interview_frontier` | 计算访谈前沿 (本轮可问问题) | — |
| `interview_pending_facts` | 收集待查环境事实 | — |
| `interview_progress` / `is_interview_complete` | 访谈进度/完成判定 | — |
| `record_interview_answers` / `record_interview_facts` | 记录答案/事实 | — |
| `resolve_interview_answer` | 确定性推荐答案 | — |
| `scan_standards` | Standards 轴坏味道扫描 (确定性) | — |
| `scan_spec_coverage` / `review_diff` | Spec 轴范围比对 / 双轴合并审查 | — |
| `read_glossary` / `upsert_term` | CONTEXT.md 术语表读写 | — |
| `should_write_adr` / `write_adr` | ADR 三门槛 / 编号落盘 | — |
| `tickets_next_runnable` / `ticket_set_status` | 票阻塞边解算 / 状态流转 | — |
| `tickets_check_cycles` | 依赖环检测 | — |
| `pipeline_next_action` / `pipeline_transition` | 阶段机下一步/迁移 | — |
