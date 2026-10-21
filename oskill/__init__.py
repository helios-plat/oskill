"""Oskill — Composite financial analysis workflows built on oprim atomic operations. Lazy-loaded."""

from __future__ import annotations
import ast
import importlib
from pathlib import Path
from typing import Any
from oskill._version import __version__

_ELEMENT_MAP: dict[str, str] = {}
_SUBMODULE_SET: set[str] = set()


def _build_element_map() -> None:
    pkg_dir = Path(__file__).parent
    pkg_name = __package__ or "oskill"
    for py in sorted(pkg_dir.rglob("*.py")):
        rel_path = py.relative_to(pkg_dir)
        if rel_path.parts == ("__init__.py",):
            continue
        mod_parts = list(rel_path.with_suffix("").parts)
        if mod_parts[-1] == "__init__":
            mod_parts.pop()
        if not mod_parts:
            continue
        mod_path = pkg_name + "." + ".".join(mod_parts)
        stem = mod_parts[-1]
        _SUBMODULE_SET.add(stem)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in tree.body:
                names = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.append(node.name)
                elif isinstance(node, ast.ImportFrom) and rel_path.name == "__init__.py":
                    for alias in node.names:
                        if alias.name != "*":
                            names.append(alias.asname or alias.name)
                for name in names:
                    if not name.startswith("_"):
                        # Heuristic: prefer non-prefixed modules, or if mapping to private, allow overwrite by public
                        if name not in _ELEMENT_MAP or (
                            not mod_path.split(".")[-1].startswith("_")
                            and _ELEMENT_MAP[name].split(".")[-1].startswith("_")
                        ):
                            _ELEMENT_MAP[name] = mod_path
        except Exception:
            continue


_build_element_map()

# Authoritative export bindings inherited from origin/main's explicit import
# surface.  The AST walk is permissive and discovers new atoms without a registry
# edit; where both lines shipped a binding for the same public name, origin/main's
# explicit ``from ... import`` is the contract and wins.
_AUTHORITATIVE_EXPORTS: dict[str, str] = {
    'A2AProtocol': 'oskill.agent_messaging',
    'ACL': 'oskill.memory_assets',
    'ACTIONABLE_ANIMATION_STABLE': 'oskill.test_stability',
    'ACTIONABLE_CHECKS': 'oskill.test_stability',
    'ACTIONABLE_CLICKABLE': 'oskill.test_stability',
    'ACTIONABLE_NOT_COVERED': 'oskill.test_stability',
    'ACTIONABLE_VISIBLE': 'oskill.test_stability',
    'ATOM_CONSTRAINT': 'oskill.memory_layers',
    'ATOM_EVENT': 'oskill.memory_layers',
    'ATOM_FACT': 'oskill.memory_layers',
    'ATOM_PREFERENCE': 'oskill.memory_layers',
    'AdrDraft': 'oskill.shared_language',
    'AgentBus': 'oskill.agent_messaging',
    'AgentMessage': 'oskill.agent_messaging',
    'AgentResult': 'oskill.agent_orchestrator',
    'AntiNoiseValidator': 'oskill.agent_discovery',
    'ApplyResult': 'oskill._types',
    'Article': 'oskill.wechat_publish',
    'ArticleStore': 'oskill.wechat_publish',
    'AssetRegistry': 'oskill.memory_assets',
    'BackendExecutor': 'oskill.runtime_backends',
    'BackendRegistry': 'oskill.runtime_backends',
    'BanditRouter': 'oskill.bandit_router',
    'BanditState': 'oskill.bandit_router',
    'BayesianBeliefUpdater': 'oskill._bayesian_belief_update',
    'BrowserRunner': 'oskill.browser_runner',
    'BrowserStepResult': 'oskill.browser_runner',
    'BuildStats': 'oskill.code_graph_builder',
    'CONTRACT_FIELDS': 'oskill._skill_contract',
    'CallEdge': 'oskill.code_parse',
    'CategoricalCPD': 'oskill._online_cpd_update',
    'CodeGraphBuilder': 'oskill.code_graph_builder',
    'CodeSymbol': 'oskill.code_parse',
    'CodeTree': 'oskill.code_parse',
    'ComparisonReport': 'oskill.eval_suite',
    'ComplianceHit': 'oskill.wechat_writing',
    'ConfigOskillError': 'oskill._types',
    'ContextBudget': 'oskill.context_engineering',
    'ContextEngine': 'oskill.context_engineering',
    'ContextItem': 'oskill.agent_context_pool',
    'ContextMessage': 'oskill.context_engineering',
    'ContextPool': 'oskill.agent_context_pool',
    'ConversationVars': 'oskill.conversation_vars',
    'DECISION_COMPONENTS': 'oskill.productization_gate',
    'DECISION_KEEP_FIELD': 'oskill.productization_gate',
    'DECISION_PRODUCTIZE': 'oskill.productization_gate',
    'DEFAULT_HYPOTHESES': 'oskill._bayesian_belief_update',
    'DEFAULT_SPECS': 'oskill.env_doctor',
    'DaemonLifecycle': 'oskill.daemon_runtime',
    'DaemonState': 'oskill.daemon_runtime',
    'DataSourceAdapter': 'oskill.doc_extractors',
    'DecisionVerdict': 'oskill.agent_discovery',
    'DepSpec': 'oskill.env_doctor',
    'DirWatcher': 'oskill.daemon_runtime',
    'DistillPipeline': 'oskill.memory_layers',
    'DoctorReport': 'oskill.env_doctor',
    'EDGE_EXTRACTED': 'oskill.knowledge_graph_query',
    'EDGE_INFERRED': 'oskill.knowledge_graph_query',
    'ENV_CN': 'oskill.social_publish',
    'ENV_INTL': 'oskill.social_publish',
    'EXTRACTED': 'oskill._edge_confidence',
    'EditBlock': 'oskill._types',
    'EditOskillError': 'oskill._types',
    'EmbeddingProvider': 'oskill.embedding_service',
    'EmbeddingService': 'oskill.embedding_service',
    'EvalCase': 'oskill.eval_suite',
    'EvalRun': 'oskill.eval_suite',
    'Experience': 'oskill.failure_learning',
    'ExperienceStore': 'oskill.failure_learning',
    'FRAMEWORK_AUTOGEN': 'oskill.agent_frameworks',
    'FRAMEWORK_LANGGRAPH': 'oskill.agent_frameworks',
    'FULL_DUPLEX_MODE': 'oskill.voice_pipeline',
    'FULL_REWRITE_CRITERIA': 'oskill.wechat_review_loop',
    'FailureRecord': 'oskill.failure_learning',
    'Finding': 'oskill.pentest_loop',
    'FlowBroker': 'oskill.flow_orchestrator',
    'FlowRegistry': 'oskill.flow_orchestrator',
    'FlowResult': 'oskill.flow_orchestrator',
    'FlowRunner': 'oskill.flow_orchestrator',
    'FlowStep': 'oskill.flow_orchestrator',
    'ForceAnalysisResult': 'oskill._physics_force_analysis_guide',
    'FrameworkRegistry': 'oskill.agent_frameworks',
    'FrameworkSpec': 'oskill.agent_frameworks',
    'GRADE_AT_RISK': 'oskill.health_score',
    'GRADE_CRITICAL': 'oskill.health_score',
    'GRADE_HEALTHY': 'oskill.health_score',
    'GateVerdict': 'oskill.svg_craft',
    'GenericHttpAdapter': 'oskill.social_publish',
    'GraphEdge': 'oskill.knowledge_graph_query',
    'GraphNode': 'oskill.knowledge_graph_query',
    'HealthAlert': 'oskill.health_score',
    'HealthMonitor': 'oskill.health_probe',
    'HealthProbe': 'oskill.health_probe',
    'HealthReport': 'oskill.health_score',
    'HookCmd': 'oskill._types',
    'INFERRED': 'oskill._edge_confidence',
    'InterviewQuestion': 'oskill.requirements_interview',
    'InterviewState': 'oskill.requirements_interview',
    'KnowledgeGraph': 'oskill.knowledge_graph_query',
    'L1Atom': 'oskill.memory_layers',
    'L2Scenario': 'oskill.memory_layers',
    'L3Persona': 'oskill.memory_layers',
    'LAYERS': 'oskill.health_score',
    'LAYER_BUSINESS': 'oskill.health_score',
    'LAYER_CUSTOMER': 'oskill.health_score',
    'LAYER_DELIVERY': 'oskill.health_score',
    'LAYER_ORG': 'oskill.health_score',
    'LEVEL_NAMES': 'oskill.svg_craft',
    'LINK_DEPENDS_ON': 'oskill.code_graph_semantic',
    'LINK_IMPLEMENTS': 'oskill.code_graph_semantic',
    'LINK_PART_OF': 'oskill.code_graph_semantic',
    'LINK_PRODUCES': 'oskill.code_graph_semantic',
    'LINK_USES': 'oskill.code_graph_semantic',
    'LLMOskillError': 'oskill._types',
    'LLMRouter': 'oskill.llm_router',
    'LadderDecision': 'oskill.svg_craft',
    'LayoutBlock': 'oskill.wechat_theme',
    'Listing': 'oskill.marketplace',
    'MEMORY_KINDS': 'oskill.memory_system',
    'MEMORY_RAG': 'oskill.memory_system',
    'MEMORY_TOOL': 'oskill.memory_system',
    'MODES': 'oskill.agent_orchestrator',
    'MODE_FUNCTION_CALLING': 'oskill.agent_orchestrator',
    'MODE_PLAN': 'oskill.agent_orchestrator',
    'MODE_REACT': 'oskill.agent_orchestrator',
    'MSG_STATUS_ERROR': 'oskill.agent_messaging',
    'MSG_STATUS_SUCCESS': 'oskill.agent_messaging',
    'Marketplace': 'oskill.marketplace',
    'MemoryAsset': 'oskill.memory_assets',
    'MemoryEntry': 'oskill.memory_layers',
    'MemoryStore': 'oskill.memory_system',
    'Metric': 'oskill.health_score',
    'ModerationRule': 'oskill.content_moderation',
    'ModerationVerdict': 'oskill.content_moderation',
    'MvdPipeline': 'oskill.mvd',
    'MvdVerdict': 'oskill.mvd',
    'NODE_CONDITION': 'oskill.workflow_dsl',
    'NODE_END': 'oskill.workflow_dsl',
    'NODE_ITERATION': 'oskill.workflow_dsl',
    'NODE_KNOWLEDGE': 'oskill.workflow_dsl',
    'NODE_LLM': 'oskill.workflow_dsl',
    'NODE_START': 'oskill.workflow_dsl',
    'NODE_TOOL': 'oskill.workflow_dsl',
    'NODE_VARIABLE': 'oskill.workflow_dsl',
    'OffloadPipeline': 'oskill.memory_offload',
    'OskillError': 'oskill._types',
    'PHASES': 'oskill.mvd',
    'PIPE_MODE': 'oskill.voice_pipeline',
    'PLACEHOLDER_RE': 'oskill.verity_check',
    'PLATFORM_TIKTOK': 'oskill.social_publish',
    'PLATFORM_WECHAT': 'oskill.social_publish',
    'PLATFORM_XIAOHONGSHU': 'oskill.social_publish',
    'PLATFORM_YOUTUBE': 'oskill.social_publish',
    'PRESETS': 'oskill.spec_execute',
    'PROVIDER_REGISTRY': 'oskill.provider_clients',
    'ParseOskillError': 'oskill._types',
    'PathAudit': 'oskill.svg_craft',
    'PathSegment': 'oskill.svg_craft',
    'PentestReport': 'oskill.pentest_loop',
    'PentestState': 'oskill.pentest_loop',
    'PipelineAction': 'oskill.workflow_pipeline',
    'PlatformAdapter': 'oskill.social_publish',
    'PlatformCapabilities': 'oskill.social_publish',
    'PlatformCredential': 'oskill.social_publish',
    'PlaybookLibrary': 'oskill.playbook',
    'PluginDecl': 'oskill.plugin_registry',
    'PluginManifest': 'oskill._types',
    'PluginRegistry': 'oskill.plugin_registry',
    'Principal': 'oskill.memory_assets',
    'ProbeState': 'oskill.health_probe',
    'ProductizationVerdict': 'oskill.productization_gate',
    'ProviderClient': 'oskill.provider_clients',
    'PublishResult': 'oskill.social_publish',
    'ROLES': 'oskill.pentest_squad',
    'RULEBOOK_KEYWORDS': 'oskill.rulebooks',
    'RULES': 'oskill.mvd',
    'RagIndex': 'oskill.rag_pipeline',
    'ReadingGuideResult': 'oskill._reading_comprehension_guide',
    'RecurringScheduler': 'oskill.recurring_scheduler',
    'ReflectionLoop': 'oskill.reflection_agent',
    'ReflectionResult': 'oskill.reflection_agent',
    'RepoFile': 'oskill._types',
    'RepoMap': 'oskill._types',
    'Resource': 'oskill.agent_discovery',
    'ResourceCatalog': 'oskill.agent_discovery',
    'RetrievalBudget': 'oskill.rrf_retrieval',
    'ReviewFinding': 'oskill.review_double_axis',
    'ReviewIssue': 'oskill.wechat_review_loop',
    'ReviewReport': 'oskill.review_double_axis',
    'ReviewRound': 'oskill.wechat_review_loop',
    'RewardRule': 'oskill.agentic_rl',
    'RunResult': 'oskill.test_stability',
    'RuntimeBackend': 'oskill.runtime_backends',
    'SCOPE_PROJECT': 'oskill.conversation_vars',
    'SCOPE_SESSION': 'oskill.conversation_vars',
    'SECTIONS': 'oskill.playbook',
    'SETTLEMENT_FIXED': 'oskill.social_publish',
    'SETTLEMENT_PER_UNIT': 'oskill.social_publish',
    'SETTLEMENT_REVENUE_SHARE': 'oskill.social_publish',
    'STAGE_EVAL': 'oskill.agentic_rl',
    'STAGE_RL': 'oskill.agentic_rl',
    'STAGE_RM': 'oskill.agentic_rl',
    'STAGE_SFT': 'oskill.agentic_rl',
    'STATUS_CLAIMED': 'oskill.marketplace',
    'STATUS_DELIVERED': 'oskill.marketplace',
    'STATUS_ERROR': 'oskill.health_probe',
    'STATUS_HEALTHY': 'oskill.health_probe',
    'STATUS_INVALID': 'oskill.health_probe',
    'STATUS_NEEDS_INFO': 'oskill.triage_flow',
    'STATUS_NEEDS_TRIAGE': 'oskill.triage_flow',
    'STATUS_OPEN': 'oskill.marketplace',
    'STATUS_RATE_LIMITED': 'oskill.health_probe',
    'STATUS_READY_AGENT': 'oskill.triage_flow',
    'STATUS_READY_HUMAN': 'oskill.triage_flow',
    'STATUS_SETTLED': 'oskill.marketplace',
    'STATUS_WONTFIX': 'oskill.triage_flow',
    'STRATEGY_NAMES': 'oskill._strategy_evolve',
    'STRATEGY_PARAMS': 'oskill._strategy_evolve',
    'STREAM_MODE': 'oskill.voice_pipeline',
    'STYLE_BOX': 'oskill.drawio_diagram',
    'STYLE_DATA': 'oskill.drawio_diagram',
    'STYLE_DECISION': 'oskill.drawio_diagram',
    'STYLE_EDGE': 'oskill.drawio_diagram',
    'STYLE_PROCESS': 'oskill.drawio_diagram',
    'SYMBOL_CLASS': 'oskill.code_parse',
    'SYMBOL_FUNCTION': 'oskill.code_parse',
    'SYMBOL_IMPORT': 'oskill.code_parse',
    'SYMBOL_METHOD': 'oskill.code_parse',
    'ScenarioPlaybook': 'oskill.playbook',
    'Scorer': 'oskill.eval_suite',
    'SecureStore': 'oskill.secure_store',
    'SecureStoreError': 'oskill.secure_store',
    'SemanticBuild': 'oskill.code_graph_semantic',
    'SemanticNode': 'oskill.code_graph_semantic',
    'SocialTask': 'oskill.social_publish',
    'SocraticStateV2': 'oskill.socratic_guide_v2',
    'SourceRef': 'oskill.code_graph_semantic',
    'SpecExecutor': 'oskill.spec_execute',
    'SquadFinding': 'oskill.pentest_squad',
    'SquadOrchestrator': 'oskill.pentest_squad',
    'SquadReport': 'oskill.pentest_squad',
    'StrategyEvolver': 'oskill._strategy_evolve',
    'SubTask': 'oskill._types',
    'Symbol': 'oskill._types',
    'SyncSession': 'oskill.daemon_runtime',
    'TICKET_BLOCKED': 'oskill.workflow_pipeline',
    'TICKET_DONE': 'oskill.workflow_pipeline',
    'TICKET_OPEN': 'oskill.workflow_pipeline',
    'TYPST_GUIDE': 'oskill.typst_author',
    'TaskSegment': 'oskill.memory_offload',
    'TestCaseResult': 'oskill.test_report',
    'TestRunReport': 'oskill.test_report',
    'Ticket': 'oskill.workflow_pipeline',
    'TodoItem': 'oskill._types',
    'ToolCall': 'oskill._types',
    'ToolMemory': 'oskill.memory_system',
    'TrainPipeline': 'oskill.agentic_rl',
    'TriageFlow': 'oskill.triage_flow',
    'TriageIssue': 'oskill.triage_flow',
    'TrimResult': 'oskill.context_engineering',
    'UndoPlan': 'oskill._types',
    'VISIBILITY_DERIVED': 'oskill.agent_context_pool',
    'VISIBILITY_ISOLATED': 'oskill.agent_context_pool',
    'VISIBILITY_PRIVATE': 'oskill.memory_assets',
    'VISIBILITY_RESTRICTED': 'oskill.memory_assets',
    'VISIBILITY_SHARED': 'oskill.agent_context_pool',
    'VISIBILITY_TEAM': 'oskill.memory_assets',
    'VarEntry': 'oskill.conversation_vars',
    'VerityConfig': 'oskill.verity_check',
    'VerityItem': 'oskill.verity_check',
    'VerityReport': 'oskill.verity_check',
    'VoiceTurn': 'oskill.voice_pipeline',
    'WechatAccount': 'oskill.wechat_publish',
    'WechatAccountRegistry': 'oskill.wechat_publish',
    'WechatAdapter': 'oskill.social_publish',
    'WechatReviewLoop': 'oskill.wechat_review_loop',
    'WechatTheme': 'oskill.wechat_theme',
    'WiringResult': 'oskill.agent_wiring',
    'WorkflowDAG': 'oskill.workflow_dsl',
    'WorkflowNode': 'oskill.workflow_dsl',
    'WorkflowState': 'oskill.workflow_pipeline',
    '__version__': 'oskill._version',
    '_bayesian_belief_update': 'oskill._bayesian_belief_update',
    'adapt_call': 'oskill.fn_call_adapter',
    'advise_prompt': 'oskill.wechat_writing',
    'agent_form_synthesize': 'oskill.agent_form_synthesize',
    'allocate_gift_card_balance': 'oskill._allocate_gift_card_balance',
    'annotate_edges': 'oskill._edge_confidence',
    'apply_discount_amount': 'oskill._apply_discount_amount',
    'apply_discount_percentage': 'oskill._apply_discount_percentage',
    'apply_edit_block': 'oskill._apply_edit_block',
    'apply_free_shipping': 'oskill._apply_free_shipping',
    'apply_theme': 'oskill.wechat_theme',
    'apply_todo_update': 'oskill._apply_todo_update',
    'apply_unified_diff': 'oskill._apply_unified_diff',
    'batch_draft': 'oskill.social_publish',
    'bm25_score': 'oskill.rrf_retrieval',
    'build_definition_index': 'oskill._edge_confidence',
    'build_fingerprint': 'oskill.code_graph_semantic',
    'build_rag_pipeline': 'oskill.rag_pipeline',
    'build_repo_context': 'oskill._build_repo_context',
    'build_subagent_prompt': 'oskill._build_subagent_prompt',
    'build_undo_plan': 'oskill._build_undo_plan',
    'cascade_delete': 'oskill._cascade_delete',
    'catalog_summary': 'oskill.wechat_resources',
    'check_dependencies': 'oskill.env_doctor',
    'chunk_code': 'oskill._chunk_code',
    'chunk_text': 'oskill.rag_pipeline',
    'clean_document': 'oskill.rag_pipeline',
    'client_for': 'oskill.provider_clients',
    'cohens_d': 'oskill.eval_suite',
    'cold_start_single': 'oskill.cold_start_single',
    'collect_test_run': 'oskill.test_report',
    'compare_runs': 'oskill.eval_suite',
    'compile_paper': 'oskill.verity_check',
    'complexity_ladder': 'oskill.svg_craft',
    'compliance_report': 'oskill.wechat_writing',
    'compose_plugin_manifest': 'oskill._compose_plugin_manifest',
    'compress_context': 'oskill._compress_context',
    'compute_cart_grand_total': 'oskill._compute_cart_grand_total',
    'compute_cart_subtotal': 'oskill._compute_cart_subtotal',
    'compute_health': 'oskill.health_score',
    'compute_reward': 'oskill.agentic_rl',
    'config_key': 'oskill._online_cpd_update',
    'conflict_resolution': 'oskill._conflict_resolution',
    'content_hash': 'oskill.code_graph_semantic',
    'content_limits': 'oskill.social_publish',
    'convert_to_tool_calls': 'oskill.fn_call_adapter',
    'cover_prompt': 'oskill.wechat_writing',
    'create_image_post': 'oskill.wechat_publish',
    'dag_visual_layout': 'oskill.dag_visual_layout',
    'dedup_edits': 'oskill._dedup_edits',
    'deep_research_tree': 'oskill.deep_research_tree',
    'derive_key': 'oskill.secure_store',
    'detect_platform': 'oskill.env_doctor',
    'dirichlet_update': 'oskill._online_cpd_update',
    'drawio_doc': 'oskill.drawio_diagram',
    'drawio_edge': 'oskill.drawio_diagram',
    'drawio_node': 'oskill.drawio_diagram',
    'dsl_to_framework': 'oskill.agent_frameworks',
    'edge_confidence': 'oskill._edge_confidence',
    'ema_update': 'oskill._online_cpd_update',
    'escalate_thinking_budget': 'oskill._escalate_thinking_budget',
    'essay_guide': 'oskill.essay_guide',
    'evaluate_discount_conditions': 'oskill._evaluate_discount_conditions',
    'evaluate_discount_eligibility': 'oskill._evaluate_discount_eligibility',
    'evaluate_hooks': 'oskill._evaluate_hooks',
    'evaluate_productization': 'oskill.productization_gate',
    'expect_eventually': 'oskill.test_stability',
    'export_drawio': 'oskill.drawio_diagram',
    'extract_contract': 'oskill._skill_contract',
    'extract_docx': 'oskill.doc_extractors',
    'extract_pdf': 'oskill.doc_extractors',
    'extract_symbols': 'oskill._extract_symbols',
    'extract_text': 'oskill.doc_extractors',
    'extract_variables': 'oskill.template_engine',
    'extract_xlsx': 'oskill.doc_extractors',
    'fan_out_and_synthesize': 'oskill._fan_out_synthesize',
    'fetch_url': 'oskill.doc_extractors',
    'fit_smooth_cubic': 'oskill.svg_path_tools',
    'format_diagnostics': 'oskill._format_diagnostics',
    'format_experiences': 'oskill.failure_learning',
    'format_skill_contract_block': 'oskill._skill_contract',
    'generate_patch_preview': 'oskill._generate_patch_preview',
    'get_platform': 'oskill.social_publish',
    'get_rulebook': 'oskill.rulebooks',
    'get_theme': 'oskill.wechat_theme',
    'graph_expand_retrieval': 'oskill._graph_expand_retrieval',
    'grpo_advantages': 'oskill.agentic_rl',
    'has_contract': 'oskill._skill_contract',
    'humanize_prompt': 'oskill.wechat_writing',
    'hybrid_search': 'oskill.rrf_retrieval',
    'incremental_refresh': 'oskill.code_graph_semantic',
    'infographic_prompt': 'oskill.wechat_writing',
    'inspect_article': 'oskill.wechat_publish',
    'install_commands': 'oskill.env_doctor',
    'interrupt_turn': 'oskill.voice_pipeline',
    'interview_frontier': 'oskill.requirements_interview',
    'interview_pending_facts': 'oskill.requirements_interview',
    'interview_progress': 'oskill.requirements_interview',
    'iou_score': 'oskill.svg_craft',
    'is_function_call_output': 'oskill.fn_call_adapter',
    'is_interview_complete': 'oskill.requirements_interview',
    'is_low_confidence': 'oskill._edge_confidence',
    'layout_modules': 'oskill.wechat_theme',
    'leader_worker_dispatch': 'oskill.leader_worker_dispatch',
    'list_agents': 'oskill.agent_wiring',
    'list_figure_templates': 'oskill.figure_templates',
    'list_platforms': 'oskill.social_publish',
    'list_rulebooks': 'oskill.rulebooks',
    'list_themes': 'oskill.wechat_theme',
    'llm_router': 'oskill.llm_router',
    'load_document': 'oskill.rag_pipeline',
    'load_skill_progressive': 'oskill._load_skill_progressive',
    'mark_no_function_calling': 'oskill.fn_call_adapter',
    'mark_settled': 'oskill.social_publish',
    'match_permission_rule': 'oskill._match_permission_rule',
    'md_to_wechat_html': 'oskill.wechat_publish',
    'merge_config': 'oskill._merge_config',
    'merge_revision': 'oskill.wechat_review_loop',
    'merge_subagent_result': 'oskill._merge_subagent_result',
    'meta_self_develop_loop': 'oskill.meta_self_develop_loop',
    'metacog_scaffold': 'oskill.metacog_scaffold',
    'moderate': 'oskill.content_moderation',
    'moderate_with_llm': 'oskill.content_moderation',
    'monthly_clamp': 'oskill.scheduler_attempt_lifecycle',
    'mvd_check': 'oskill.mvd',
    'needs_adapter': 'oskill.fn_call_adapter',
    'needs_full_rewrite': 'oskill.wechat_review_loop',
    'normalize': 'oskill.health_score',
    'paired_t_test': 'oskill.eval_suite',
    'parse_code': 'oskill.code_parse',
    'parse_dsl': 'oskill.workflow_dsl',
    'parse_dsl_json': 'oskill.workflow_dsl',
    'parse_function_tags': 'oskill.fn_call_adapter',
    'parse_layout_blocks': 'oskill.wechat_theme',
    'parse_llm_tool_calls': 'oskill._parse_llm_tool_calls',
    'parse_path': 'oskill.svg_craft',
    'parse_python_tree': 'oskill.code_parse',
    'parse_verdict': 'oskill.wechat_review_loop',
    'parse_wikilinks': 'oskill.code_graph_semantic',
    'path_bbox': 'oskill.svg_path_tools',
    'path_center': 'oskill.svg_path_tools',
    'pdf_pages': 'oskill.verity_check',
    'physics_force_analysis_guide': 'oskill._physics_force_analysis_guide',
    'pipeline_next_action': 'oskill.workflow_pipeline',
    'pipeline_transition': 'oskill.workflow_pipeline',
    'plan_decompose': 'oskill._plan_decompose',
    'plan_to_todos': 'oskill._plan_to_todos',
    'plan_wiring': 'oskill.agent_wiring',
    'pre_run_knowledge_hook': 'oskill.scheduler_attempt_lifecycle',
    'produce_article': 'oskill.wechat_publish',
    'publish_draft': 'oskill.wechat_publish',
    'publish_to': 'oskill.social_publish',
    'rank_relevant_files': 'oskill._rank_relevant_files',
    'read_glossary': 'oskill.shared_language',
    'reading_comprehension_guide': 'oskill._reading_comprehension_guide',
    'record_interview_answers': 'oskill.requirements_interview',
    'record_interview_facts': 'oskill.requirements_interview',
    'register_layout_module': 'oskill.wechat_theme',
    'register_platform': 'oskill.social_publish',
    'register_theme': 'oskill.wechat_theme',
    'register_wechat_resources': 'oskill.wechat_resources',
    'relevance_compute': 'oskill._relevance_compute',
    'render_cubic_path': 'oskill.svg_path_tools',
    'render_drawio': 'oskill.drawio_diagram',
    'render_figure_template': 'oskill.figure_templates',
    'render_layout_block': 'oskill.wechat_theme',
    'render_markdown_with_layout': 'oskill.wechat_theme',
    'render_node_markdown': 'oskill.code_graph_semantic',
    'render_preset': 'oskill.spec_execute',
    'render_template': 'oskill.template_engine',
    'repo_map_build': 'oskill._repo_map_build',
    'resolve_config': 'oskill.verity_check',
    'resolve_display_batch': 'oskill._resolve_display_batch',
    'resolve_interview_answer': 'oskill.requirements_interview',
    'resolve_memory_hierarchy': 'oskill._resolve_memory_hierarchy',
    'resolve_mentions': 'oskill._resolve_mentions',
    'resolve_template': 'oskill.figure_templates',
    'retry_execute': 'oskill.scheduler_attempt_lifecycle',
    'retry_until': 'oskill.test_stability',
    'review_diff': 'oskill.review_double_axis',
    'reviewer_prompt': 'oskill.wechat_writing',
    'reviser_prompt': 'oskill.wechat_writing',
    'rrf_merge': 'oskill.rrf_retrieval',
    'rules_sections': 'oskill.rulebooks',
    'run_agent': 'oskill.agent_orchestrator',
    'run_browser_test': 'oskill.browser_runner',
    'run_doctor': 'oskill.env_doctor',
    'run_function_calling': 'oskill.agent_orchestrator',
    'run_pentest_loop': 'oskill.pentest_loop',
    'run_plan': 'oskill.agent_orchestrator',
    'run_react': 'oskill.agent_orchestrator',
    'run_suite': 'oskill.eval_suite',
    'run_text_gate': 'oskill.verity_check',
    'run_verity': 'oskill.verity_check',
    'run_voice_pipeline': 'oskill.voice_pipeline',
    'scan_compliance': 'oskill.wechat_writing',
    'scan_spec_coverage': 'oskill.review_double_axis',
    'scan_standards': 'oskill.review_double_axis',
    'select_rulebooks': 'oskill.rulebooks',
    'select_skill': 'oskill._select_skill',
    'select_tools': 'oskill._select_tools',
    'semantic_build': 'oskill.code_graph_semantic',
    'semantic_search': 'oskill._semantic_search',
    'semantic_to_graph': 'oskill.knowledge_graph_query',
    'sequential_update': 'oskill._bayesian_belief_update',
    'settle': 'oskill.social_publish',
    'should_write_adr': 'oskill.shared_language',
    'simplify_line': 'oskill.svg_path_tools',
    'skill_export': 'oskill.skill_teach',
    'skill_import_': 'oskill.skill_teach',
    'skill_list': 'oskill.skill_teach',
    'skill_teach': 'oskill.skill_teach',
    'skills_dynamic_inject': 'oskill.skills_dynamic_inject',
    'smoothness_gate': 'oskill.svg_craft',
    'socratic_guide_v2': 'oskill.socratic_guide_v2',
    'soul_self_evolution': 'oskill.soul_self_evolution',
    'spec_executor': 'oskill.spec_execute',
    'split_config': 'oskill._online_cpd_update',
    'stack_discount_allocations': 'oskill._stack_discount_allocations',
    'stale_nodes': 'oskill.code_graph_semantic',
    'standards_rules': 'oskill.rulebooks',
    'summarize_file': 'oskill._summarize_file',
    'svg_path_audit': 'oskill.svg_craft',
    'syntax_check': 'oskill._syntax_check',
    'team_plan_gen': 'oskill.team_plan_gen',
    'three_way_merge': 'oskill._three_way_merge',
    'ticket_set_status': 'oskill.workflow_pipeline',
    'tickets_check_cycles': 'oskill.workflow_pipeline',
    'tickets_next_runnable': 'oskill.workflow_pipeline',
    'title_prompt': 'oskill.wechat_writing',
    'tokenize': 'oskill.rrf_retrieval',
    'tools_to_prompt': 'oskill.fn_call_adapter',
    'topological_execute': 'oskill.workflow_dsl',
    'transition_attempt': 'oskill.scheduler_attempt_lifecycle',
    'two_step_ingest': 'oskill._two_step_ingest',
    'typst_compile': 'oskill.typst_author',
    'typst_format_check': 'oskill.typst_author',
    'typst_minimal_doc': 'oskill.typst_author',
    'typst_probe': 'oskill.typst_author',
    'update_cpd': 'oskill._online_cpd_update',
    'upload_image': 'oskill.wechat_publish',
    'upsert_term': 'oskill.shared_language',
    'validate_drawio': 'oskill.drawio_diagram',
    'validate_dsl': 'oskill.workflow_dsl',
    'validate_edit': 'oskill._validate_edit',
    'validate_skill_contract': 'oskill._skill_contract',
    'variant_for_review': 'oskill.variant_for_review',
    'verify_finding': 'oskill.pentest_loop',
    'wait_actionable': 'oskill.test_stability',
    'watchdog': 'oskill.health_score',
    'wechat_catalog': 'oskill.wechat_resources',
    'wilcoxon_signed_rank': 'oskill.eval_suite',
    'workflow_from_dict': 'oskill.workflow_pipeline',
    'workflow_to_dict': 'oskill.workflow_pipeline',
    'worktree_conflict_resolve': 'oskill.worktree_conflict_resolve',
    'wrap_tools': 'oskill.fn_call_adapter',
    'write_adr': 'oskill.shared_language',
    'write_agent_instructions': 'oskill.agent_wiring',
    'write_prompt': 'oskill.wechat_writing',
}
_AUTHORITATIVE_EXPORTS["tradingview_market_snapshot"] = "oskill.tradingview_market_snapshot"
_ELEMENT_MAP.update(_AUTHORITATIVE_EXPORTS)


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return __version__
    if name in _ELEMENT_MAP:
        mod = importlib.import_module(_ELEMENT_MAP[name])
        # Special case for FusedResult/SearchResult aliases in merge_platform_user_results
        actual_name = name
        if name == "MergedFusedResult":
            actual_name = "FusedResult"
        if name == "MergedSearchResult":
            actual_name = "SearchResult"
        return getattr(mod, actual_name)
    if name in _SUBMODULE_SET:
        pkg_name = __package__ or "oskill"
        return importlib.import_module(f"{pkg_name}.{name}")
    raise AttributeError(f"module '{__name__}' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(_ELEMENT_MAP.keys()) + list(_SUBMODULE_SET) + ["__version__"]))


__all__ = sorted(_ELEMENT_MAP.keys())

# --- Explicit re-exports (Pinning) ---
from oskill._types import (
    OskillError,
    EditOskillError,
    ParseOskillError,
    LLMOskillError,
    ConfigOskillError,
    EditBlock,
    ApplyResult,
    Chunk,
    Symbol,
    RepoFile,
    RepoMap,
    TodoItem,
    SubTask,
    ToolCall,
    PluginManifest,
    UndoPlan,
    HookCmd,
)
from oskill._apply_edit_block import apply_edit_block
from oskill._apply_unified_diff import apply_unified_diff
from oskill._select_tools import select_tools
from oskill._select_skill import select_skill
from oskill._plan_decompose import plan_decompose
from oskill._plan_to_todos import plan_to_todos
from oskill._apply_todo_update import apply_todo_update
from oskill._summarize_file import summarize_file
from oskill._chunk_code import chunk_code
from oskill._extract_symbols import extract_symbols
from oskill._repo_map_build import repo_map_build
from oskill._rank_relevant_files import rank_relevant_files
from oskill._build_repo_context import build_repo_context
from oskill._semantic_search import semantic_search
from oskill._syntax_check import syntax_check
from oskill._validate_edit import validate_edit
from oskill._dedup_edits import dedup_edits
from oskill._generate_patch_preview import generate_patch_preview
from oskill._build_undo_plan import build_undo_plan
from oskill._format_diagnostics import format_diagnostics
from oskill.socratic_guide_v2 import socratic_guide_v2, SocraticStateV2
from oskill.metacog_scaffold import metacog_scaffold
from oskill.cold_start_single import cold_start_single
from oskill.variant_for_review import variant_for_review
from oskill.essay_guide import essay_guide
from oskill._parse_llm_tool_calls import parse_llm_tool_calls
from oskill._merge_config import merge_config
from oskill._evaluate_hooks import evaluate_hooks
from oskill._match_permission_rule import match_permission_rule
from oskill._escalate_thinking_budget import escalate_thinking_budget
from oskill._compose_plugin_manifest import compose_plugin_manifest
from oskill._build_subagent_prompt import build_subagent_prompt
from oskill._merge_subagent_result import merge_subagent_result
from oskill._compress_context import compress_context
from oskill._resolve_mentions import resolve_mentions
from oskill._resolve_memory_hierarchy import resolve_memory_hierarchy
from oskill._load_skill_progressive import load_skill_progressive
from oskill._three_way_merge import three_way_merge

from oskill._physics_force_analysis_guide import physics_force_analysis_guide, ForceAnalysisResult
from oskill._reading_comprehension_guide import reading_comprehension_guide, ReadingGuideResult

# ── AII Graph Capability (K-G1 … K-G5) ──────────────────────────────────────
# K-G1: LLM-confirmed conflict resolution (grade hardcoded unverified)
from oskill._conflict_resolution import conflict_resolution

# K-G2: two-pass CoT knowledge extraction (analyze → generate, no free-play)
from oskill._two_step_ingest import two_step_ingest

# K-G3: composite KU relevance scoring (direct/source/adamic/type weights)
from oskill._relevance_compute import relevance_compute

# K-G4: BFS graph expansion with relevance pruning
from oskill._graph_expand_retrieval import graph_expand_retrieval

# K-G5: safe cascade delete (dry_run=True default; shared KUs preserved)
from oskill._cascade_delete import cascade_delete

# ── Batch-warehouse commerce vertical ───────────────────────────────────────
from oskill._resolve_display_batch import resolve_display_batch
from oskill._compute_cart_subtotal import compute_cart_subtotal
from oskill._compute_cart_grand_total import compute_cart_grand_total
from oskill._evaluate_discount_eligibility import evaluate_discount_eligibility
from oskill._evaluate_discount_conditions import evaluate_discount_conditions
from oskill._apply_discount_amount import apply_discount_amount
from oskill._apply_discount_percentage import apply_discount_percentage
from oskill._apply_free_shipping import apply_free_shipping
from oskill._stack_discount_allocations import stack_discount_allocations
from oskill._allocate_gift_card_balance import allocate_gift_card_balance
from oskill._compute_tax_lines import compute_tax_lines
from oskill._compute_line_item_totals import compute_line_item_totals
from oskill._select_region_currency import select_region_currency
from oskill._evaluate_tax_inclusive_pricing import evaluate_tax_inclusive_pricing

# ── repo3o intake elements ──────────────────────────────────────────────────
from oskill._highlight_detection_algorithm import highlight_detection_algorithm
from oskill._query_expansion import query_expansion
from oskill._search_synthesize_loop import search_synthesize_loop
from oskill._dialogue_script_generation import dialogue_script_generation
from oskill._multi_speaker_tts_merge import multi_speaker_tts_merge
from oskill._video_subtitle_align import video_subtitle_align
from oskill._template_scene_compose import template_scene_compose
from oskill._multimodal_index_pipeline import multimodal_index_pipeline

# Public functions whose implementation module has the same name as the
# function. Keep these bound after submodule imports so ``from oskill import
# name`` always yields the callable, not the module object.
from oskill.dag_visual_layout import dag_visual_layout as dag_visual_layout
from oskill.deep_research_tree import deep_research_tree as deep_research_tree
from oskill.leader_worker_dispatch import leader_worker_dispatch as leader_worker_dispatch
from oskill.soul_self_evolution import soul_self_evolution as soul_self_evolution
from oskill.worktree_conflict_resolve import (
    worktree_conflict_resolve as worktree_conflict_resolve,
)
