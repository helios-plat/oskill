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

## Group 8: Rulebooks (agent-rules-books 3O 内化, v4.18.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `list_rulebooks` | 列出 14 本规则书 id | — |
| `get_rulebook` | 读某书 full 规则全文 | — |
| `rules_sections` | 按 ## 通用分段解析 | — |
| `select_rulebooks` | 按任务关键词+书名加权选书 | — |
| `standards_rules` | 拼装审查/重构规则基线 | `select_rulebooks`, `get_rulebook` |

## Group 9: Agent Book (ai-agent-book 3O 内化, v4.19.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `run_suite` | 声明式评测跑分 | `EvalCase`, scorer 注入 |
| `compare_runs` / `paired_t_test` / `wilcoxon_signed_rank` / `cohens_d` | 双跑对比 + 统计显著性 (纯 Python) | — |
| `ExperienceStore` / `format_experiences` | 失败学习: 记录/归纳/检索/注入 | — |
| `ContextPool` | 多 Agent 上下文共享/隔离投影 | — |
| `run_voice_pipeline` / `interrupt_turn` | 语音三范式编排 | asr/llm/tts 注入 |

## Group 10: md2wechat (Discovery-First + 公众号发布 3O 内化, v4.20.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `ResourceCatalog` | Discovery-First 资源目录 (注册/discover/show/capabilities) | — |
| `AntiNoiseValidator` | 5 条反噪声决策检查 (可观察/确定性/可解释/无副作用/防真实错误) | — |
| `md_to_wechat_html` | 确定性 Markdown→微信 HTML 转换 | — |
| `produce_article` | Article 组装 (标题/摘要/封面/正文) | `md_to_wechat_html` |
| `ArticleStore` | 本地草稿 + readiness 发布前检查 | — |
| `publish_draft` | 微信草稿 API (HTTP 注入) | — |

## Group 11: Graft (语义节点图 + 多 agent 接线, v4.21.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `semantic_build` | 两遍构建语义节点图 (文件摘要→分组, LLM 注入) | `build_fingerprint` |
| `incremental_refresh` / `stale_nodes` | 内容哈希指纹刷新, 只重建变更 ($0) | — |
| `render_node_markdown` / `parse_wikilinks` | 节点 markdown 渲染 / [[wikilinks]] 跟随 | — |
| `write_agent_instructions` / `plan_wiring` / `list_agents` | 多 agent 指令文件集成 (marker-fenced/owned, dry-run) | — |

## Group 12: Graphify + Strix (图遍历查询 + 渗透闭环, v4.22.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `KnowledgeGraph` | 图遍历查询 (neighbors/shortest_path/trace/communities) + EXTRACTED/INFERRED 信任分级 | — |
| `semantic_to_graph` | Graft 语义节点 → 知识图谱 (显式边 EXTRACTED, 共现 INFERRED) | `code_graph_semantic` |
| `run_pentest_loop` | 渗透闭环 (侦察→利用→验证→报告) | `verify_finding` |
| `verify_finding` | PoC 验证门 (confirmed/rejected, 防误报) | — |
| `PentestReport` | 产物契约 (markdown / SARIF 2.1.0) | — |

## Group 13: TencentDB Agent Memory (分层记忆 + 混合检索 + 资产负载, v4.23.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `rrf_merge` / `hybrid_search` / `bm25_score` | RRF 混合检索 (稀疏+稠密融合, 预算截断) | — |
| `DistillPipeline` | L0-L3 分层蒸馏 (原子 score 门控, 场景/人格构建) | — |
| `AssetRegistry` | 记忆资产注册 + private/team/restricted ACL + loadout 装配 | — |

## Group 14: Cypress (测试稳定性三机制, v4.24.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `retry_until` | 命令自动重试 (retry-ability, 默认 4s 超时, 轨迹可审计) | — |
| `wait_actionable` | Actionability 等待 (可见/可点/不遮挡/动画稳定, 检查器注入) | — |
| `expect_eventually` | 断言轮询收敛 (TDD 语义) | — |

## Group 15: FDE Book (四层健康分 + 预警干预, v4.25.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `compute_health` | 四层加权健康分 + 分档 + 预警 (delivery/customer/business/org) | `normalize` |
| `watchdog` | 周期性评估 → 预警 → 干预 (可接 notification_center) | `compute_health` |
| `normalize` | 指标值 0-100 归一化 (high/low better) | — |

## Group 16: AiToEarn (多平台发布 + 变现, v4.26.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `register_platform` / `list_platforms` | 平台适配器注册表 (Discovery-First) | — |
| `publish_to` / `content_limits` | 发布路由 (环境校验) / 平台限制查询 | `PlatformCapabilities` |
| `batch_draft` | 多平台批量草稿 (限制内裁剪) | `content_limits` |
| `settle` / `SocialTask` | 变现结算 (fixed/按量/分成) | — |
| `WechatAdapter` | 微信适配器 (复用 wechat_publish) | `wechat_publish` |

## Group 17: Pixel2Motion (SVG 拟合工艺, v4.27.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `iou_score` | mask 像素重合度 (纯 Python) | — |
| `svg_path_audit` | path d 解析 + 切线跳跃/交替小段/像素阶梯审计 | `parse_path` |
| `smoothness_gate` | Smoothness Gate 硬门槛 (阶梯/抖动/网格正交即失败) | `svg_path_audit` |
| `complexity_ladder` | 5 级复杂度阶梯决策 (升级条件表) | — |

## Group 18: FDE Book 2/7章 (MVD + 打法手册 + 产品化四问, v4.28.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `mvd_check` / `MvdPipeline` | MVD 三军规检查 + 五步流水线 (Day0-5) | — |
| `PlaybookLibrary` / `ScenarioPlaybook` | 场景七件套 + 生命周期 (负责人/版本/折旧) | — |
| `evaluate_productization` | 产品化四问决策 (productize/components/keep_field) | — |

## Group 19: Auto-Deep-Research (非函数调用 LLM 适配, v4.29.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `tools_to_prompt` | OpenAI tools → 文本描述 (AutoAgent 格式) | — |
| `wrap_tools` | 注入 system prompt (格式指令 + 描述) | `tools_to_prompt` |
| `parse_function_tags` / `convert_to_tool_calls` | <function> 标签解析 → OpenAI tool_calls | — |
| `adapt_call` | 与 model_routing 组合 (标记 provider 自动适配) | 上述全部 |

## Group 20: Dify (工作流 DSL + 模板引擎 + 插件注册表, v4.30.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `WorkflowDAG` / `topological_execute` | 工作流 DSL + DAG 拓扑执行 (并行/条件门控) | `validate_dsl` |
| `parse_dsl` / `to_dsl` | JSON DSL 序列化 (可分享/版本化) | — |
| `render_template` / `extract_variables` | {{var}} 注入 (嵌套/默认/转义/校验) | — |
| `PluginRegistry` | 插件声明 + 依赖解析 + 启用禁用级联 | — |

## Group 21: Dify Agent (三模式工具循环编排, v4.31.0)

| Skill | Description | Calls |
|-------|-------------|-------|
| `run_agent` | 统一编排入口 (按模式分派) | 下述 |
| `run_function_calling` | tool_calls 循环 (max_iteration 防死循环, 工具错误不终止) | — |
| `run_react` | Thought/Action/Observation 循环 (CoT) | — |
| `run_plan` | 计划→逐步执行→汇总 (计划器) | — |
