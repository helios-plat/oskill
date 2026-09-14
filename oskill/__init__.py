"""Oskill — Composite financial analysis workflows built on oprim atomic operations. Lazy-loaded."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

from oskill._version import __version__

_ELEMENT_MAP: dict[str, str] = {}
_SUBMODULE_SET: set[str] = set()
# 跳过扫描的包目录: 内置模板脚本等数据资产, 防止其公共函数污染顶层命名空间
_SKIP_SCAN_DIRS: frozenset[str] = frozenset({"_figure_templates"})


def _build_element_map() -> None:
    pkg_dir = Path(__file__).parent
    pkg_name = __package__ or "oskill"
    for py in sorted(pkg_dir.rglob("*.py")):
        rel_path = py.relative_to(pkg_dir)
        if rel_path.parts == ("__init__.py",):
            continue
        if any(part in _SKIP_SCAN_DIRS for part in rel_path.parts):
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
                        # Prefer public modules over private mappings.
                        if name not in _ELEMENT_MAP or (
                            not mod_path.split(".")[-1].startswith("_")
                            and _ELEMENT_MAP[name].split(".")[-1].startswith("_")
                        ):
                            _ELEMENT_MAP[name] = mod_path
        except Exception:
            continue


_build_element_map()


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
if True:
    from oskill._allocate_gift_card_balance import (
        allocate_gift_card_balance as allocate_gift_card_balance,
    )
    from oskill._apply_discount_amount import apply_discount_amount as apply_discount_amount
    from oskill._apply_discount_percentage import (
        apply_discount_percentage as apply_discount_percentage,
    )
    from oskill._apply_edit_block import apply_edit_block as apply_edit_block
    from oskill._apply_free_shipping import apply_free_shipping as apply_free_shipping
    from oskill._apply_todo_update import apply_todo_update as apply_todo_update
    from oskill._apply_unified_diff import apply_unified_diff as apply_unified_diff
    from oskill._build_repo_context import build_repo_context as build_repo_context
    from oskill._build_subagent_prompt import build_subagent_prompt as build_subagent_prompt
    from oskill._build_undo_plan import build_undo_plan as build_undo_plan

    # K-G5: safe cascade delete (dry_run=True default; shared KUs preserved)
    from oskill._cascade_delete import cascade_delete as cascade_delete
    from oskill._chunk_code import chunk_code as chunk_code
    from oskill._compose_plugin_manifest import compose_plugin_manifest as compose_plugin_manifest
    from oskill._compress_context import compress_context as compress_context
    from oskill._compute_cart_grand_total import (
        compute_cart_grand_total as compute_cart_grand_total,
    )
    from oskill._compute_cart_subtotal import compute_cart_subtotal as compute_cart_subtotal

    # ── AII Graph Capability (K-G1 … K-G5) ──────────────────────────────────────
    # K-G1: LLM-confirmed conflict resolution (grade hardcoded unverified)
    from oskill._conflict_resolution import conflict_resolution as conflict_resolution
    from oskill._dedup_edits import dedup_edits as dedup_edits
    from oskill._edge_confidence import (
        EXTRACTED as EXTRACTED,
    )
    from oskill._edge_confidence import (
        INFERRED as INFERRED,
    )
    from oskill._edge_confidence import (
        annotate_edges as annotate_edges,
    )
    from oskill._edge_confidence import (
        build_definition_index as build_definition_index,
    )
    from oskill._edge_confidence import (
        edge_confidence as edge_confidence,
    )
    from oskill._edge_confidence import (
        is_low_confidence as is_low_confidence,
    )
    from oskill._escalate_thinking_budget import (
        escalate_thinking_budget as escalate_thinking_budget,
    )
    from oskill._evaluate_discount_conditions import (
        evaluate_discount_conditions as evaluate_discount_conditions,
    )
    from oskill._evaluate_discount_eligibility import (
        evaluate_discount_eligibility as evaluate_discount_eligibility,
    )
    from oskill._evaluate_hooks import evaluate_hooks as evaluate_hooks
    from oskill._extract_symbols import extract_symbols as extract_symbols
    from oskill._fan_out_synthesize import fan_out_and_synthesize as fan_out_and_synthesize
    from oskill._format_diagnostics import format_diagnostics as format_diagnostics
    from oskill._generate_patch_preview import generate_patch_preview as generate_patch_preview

    # K-G4: BFS graph expansion with relevance pruning
    from oskill._graph_expand_retrieval import graph_expand_retrieval as graph_expand_retrieval
    from oskill._load_skill_progressive import load_skill_progressive as load_skill_progressive
    from oskill._match_permission_rule import match_permission_rule as match_permission_rule
    from oskill._merge_config import merge_config as merge_config
    from oskill._merge_subagent_result import merge_subagent_result as merge_subagent_result
    from oskill._parse_llm_tool_calls import parse_llm_tool_calls as parse_llm_tool_calls
    from oskill._physics_force_analysis_guide import (
        ForceAnalysisResult as ForceAnalysisResult,
    )
    from oskill._physics_force_analysis_guide import (
        physics_force_analysis_guide as physics_force_analysis_guide,
    )
    from oskill._plan_decompose import plan_decompose as plan_decompose
    from oskill._plan_to_todos import plan_to_todos as plan_to_todos
    from oskill._rank_relevant_files import rank_relevant_files as rank_relevant_files
    from oskill._reading_comprehension_guide import (
        ReadingGuideResult as ReadingGuideResult,
    )
    from oskill._reading_comprehension_guide import (
        reading_comprehension_guide as reading_comprehension_guide,
    )

    # K-G3: composite KU relevance scoring (direct/source/adamic/type weights)
    from oskill._relevance_compute import relevance_compute as relevance_compute
    from oskill._repo_map_build import repo_map_build as repo_map_build

    # ── Batch-warehouse commerce vertical ───────────────────────────────────────
    from oskill._resolve_display_batch import resolve_display_batch as resolve_display_batch
    from oskill._resolve_memory_hierarchy import (
        resolve_memory_hierarchy as resolve_memory_hierarchy,
    )
    from oskill._resolve_mentions import resolve_mentions as resolve_mentions
    from oskill._select_skill import select_skill as select_skill
    from oskill._select_tools import select_tools as select_tools
    from oskill._semantic_search import semantic_search as semantic_search
    from oskill._skill_contract import (
        CONTRACT_FIELDS as CONTRACT_FIELDS,
    )
    from oskill._skill_contract import (
        extract_contract as extract_contract,
    )
    from oskill._skill_contract import (
        format_skill_contract_block as format_skill_contract_block,
    )
    from oskill._skill_contract import (
        has_contract as has_contract,
    )
    from oskill._skill_contract import (
        validate_skill_contract as validate_skill_contract,
    )
    from oskill._stack_discount_allocations import (
        stack_discount_allocations as stack_discount_allocations,
    )
    from oskill._summarize_file import summarize_file as summarize_file
    from oskill._syntax_check import syntax_check as syntax_check
    from oskill._three_way_merge import three_way_merge as three_way_merge

    # K-G2: two-pass CoT knowledge extraction (analyze → generate, no free-play)
    from oskill._two_step_ingest import two_step_ingest as two_step_ingest
    from oskill._types import (
        ApplyResult as ApplyResult,
    )
    from oskill._types import (
        ConfigOskillError as ConfigOskillError,
    )
    from oskill._types import (
        EditBlock as EditBlock,
    )
    from oskill._types import (
        EditOskillError as EditOskillError,
    )
    from oskill._types import (
        HookCmd as HookCmd,
    )
    from oskill._types import (
        LLMOskillError as LLMOskillError,
    )
    from oskill._types import (
        OskillError as OskillError,
    )
    from oskill._types import (
        ParseOskillError as ParseOskillError,
    )
    from oskill._types import (
        PluginManifest as PluginManifest,
    )
    from oskill._types import (
        RepoFile as RepoFile,
    )
    from oskill._types import (
        RepoMap as RepoMap,
    )
    from oskill._types import (
        SubTask as SubTask,
    )
    from oskill._types import (
        Symbol as Symbol,
    )
    from oskill._types import (
        TodoItem as TodoItem,
    )
    from oskill._types import (
        ToolCall as ToolCall,
    )
    from oskill._types import (
        UndoPlan as UndoPlan,
    )
    from oskill._validate_edit import validate_edit as validate_edit
    from oskill.action_governance import (
        classify_action_effect as classify_action_effect,
    )
    from oskill.action_governance import (
        evaluate_action_policy as evaluate_action_policy,
    )
    from oskill.agent_context_pool import (  # noqa: E402
        VISIBILITY_DERIVED as VISIBILITY_DERIVED,
    )
    from oskill.agent_context_pool import (
        VISIBILITY_ISOLATED as VISIBILITY_ISOLATED,
    )
    from oskill.agent_context_pool import (
        VISIBILITY_SHARED as VISIBILITY_SHARED,
    )
    from oskill.agent_context_pool import (
        ContextItem as ContextItem,
    )
    from oskill.agent_context_pool import (
        ContextPool as ContextPool,
    )
    from oskill.agent_discovery import (  # noqa: E402
        AntiNoiseValidator as AntiNoiseValidator,
    )
    from oskill.agent_discovery import (
        DecisionVerdict as DecisionVerdict,
    )
    from oskill.agent_discovery import (
        Resource as Resource,
    )
    from oskill.agent_discovery import (
        ResourceCatalog as ResourceCatalog,
    )
    from oskill.agent_frameworks import (  # noqa: E402
        FRAMEWORK_AUTOGEN as FRAMEWORK_AUTOGEN,
    )
    from oskill.agent_frameworks import (
        FRAMEWORK_LANGGRAPH as FRAMEWORK_LANGGRAPH,
    )
    from oskill.agent_frameworks import (
        FrameworkRegistry as FrameworkRegistry,
    )
    from oskill.agent_frameworks import (
        FrameworkSpec as FrameworkSpec,
    )
    from oskill.agent_frameworks import (
        dsl_to_framework as dsl_to_framework,
    )
    from oskill.agent_messaging import (  # noqa: E402
        MSG_STATUS_ERROR as MSG_STATUS_ERROR,
    )
    from oskill.agent_messaging import (
        MSG_STATUS_SUCCESS as MSG_STATUS_SUCCESS,
    )
    from oskill.agent_messaging import (
        A2AProtocol as A2AProtocol,
    )
    from oskill.agent_messaging import (
        AgentBus as AgentBus,
    )
    from oskill.agent_messaging import (
        AgentMessage as AgentMessage,
    )
    from oskill.agent_orchestrator import (  # noqa: E402
        MODE_FUNCTION_CALLING as MODE_FUNCTION_CALLING,
    )
    from oskill.agent_orchestrator import (
        MODE_PLAN as MODE_PLAN,
    )
    from oskill.agent_orchestrator import (
        MODE_REACT as MODE_REACT,
    )
    from oskill.agent_orchestrator import (
        MODES as MODES,
    )
    from oskill.agent_orchestrator import (
        AgentResult as AgentResult,
    )
    from oskill.agent_orchestrator import (
        run_agent as run_agent,
    )
    from oskill.agent_orchestrator import (
        run_function_calling as run_function_calling,
    )
    from oskill.agent_orchestrator import (
        run_plan as run_plan,
    )
    from oskill.agent_orchestrator import (
        run_react as run_react,
    )
    from oskill.agent_wiring import (  # noqa: E402
        WiringResult as WiringResult,
    )
    from oskill.agent_wiring import (
        list_agents as list_agents,
    )
    from oskill.agent_wiring import (
        plan_wiring as plan_wiring,
    )
    from oskill.agent_wiring import (
        write_agent_instructions as write_agent_instructions,
    )
    from oskill.agentic_rl import (  # noqa: E402
        STAGE_EVAL as STAGE_EVAL,
    )
    from oskill.agentic_rl import (
        STAGE_RL as STAGE_RL,
    )
    from oskill.agentic_rl import (
        STAGE_RM as STAGE_RM,
    )
    from oskill.agentic_rl import (
        STAGE_SFT as STAGE_SFT,
    )
    from oskill.agentic_rl import (
        RewardRule as RewardRule,
    )
    from oskill.agentic_rl import (
        TrainPipeline as TrainPipeline,
    )
    from oskill.agentic_rl import (
        compute_reward as compute_reward,
    )
    from oskill.agentic_rl import (
        grpo_advantages as grpo_advantages,
    )
    from oskill.bandit_router import (  # noqa: E402
        BanditRouter as BanditRouter,
    )
    from oskill.bandit_router import (
        BanditState as BanditState,
    )
    from oskill.browser_runner import (  # noqa: E402
        BrowserRunner as BrowserRunner,
    )
    from oskill.browser_runner import (
        BrowserStepResult as BrowserStepResult,
    )
    from oskill.browser_runner import (
        run_browser_test as run_browser_test,
    )
    from oskill.browser_takeover import (
        browser_action_is_read as browser_action_is_read,
    )
    from oskill.browser_takeover import (
        browser_action_is_write as browser_action_is_write,
    )
    from oskill.browser_takeover import (
        classify_browser_action_effect as classify_browser_action_effect,
    )
    from oskill.browser_takeover import (
        review_browser_takeover_need as review_browser_takeover_need,
    )
    from oskill.code_graph_builder import (  # noqa: E402
        BuildStats as BuildStats,
    )
    from oskill.code_graph_builder import (
        CodeGraphBuilder as CodeGraphBuilder,
    )
    from oskill.code_graph_semantic import (  # noqa: E402
        LINK_DEPENDS_ON as LINK_DEPENDS_ON,
    )
    from oskill.code_graph_semantic import (
        LINK_IMPLEMENTS as LINK_IMPLEMENTS,
    )
    from oskill.code_graph_semantic import (
        LINK_PART_OF as LINK_PART_OF,
    )
    from oskill.code_graph_semantic import (
        LINK_PRODUCES as LINK_PRODUCES,
    )
    from oskill.code_graph_semantic import (
        LINK_USES as LINK_USES,
    )
    from oskill.code_graph_semantic import (
        SemanticBuild as SemanticBuild,
    )
    from oskill.code_graph_semantic import (
        SemanticNode as SemanticNode,
    )
    from oskill.code_graph_semantic import (
        SourceRef as SourceRef,
    )
    from oskill.code_graph_semantic import (
        build_fingerprint as build_fingerprint,
    )
    from oskill.code_graph_semantic import (
        content_hash as content_hash,
    )
    from oskill.code_graph_semantic import (
        incremental_refresh as incremental_refresh,
    )
    from oskill.code_graph_semantic import (
        parse_wikilinks as parse_wikilinks,
    )
    from oskill.code_graph_semantic import (
        render_node_markdown as render_node_markdown,
    )
    from oskill.code_graph_semantic import (
        semantic_build as semantic_build,
    )
    from oskill.code_graph_semantic import (
        stale_nodes as stale_nodes,
    )
    from oskill.code_parse import (  # noqa: E402
        SYMBOL_CLASS as SYMBOL_CLASS,
    )
    from oskill.code_parse import (
        SYMBOL_FUNCTION as SYMBOL_FUNCTION,
    )
    from oskill.code_parse import (
        SYMBOL_IMPORT as SYMBOL_IMPORT,
    )
    from oskill.code_parse import (
        SYMBOL_METHOD as SYMBOL_METHOD,
    )
    from oskill.code_parse import (
        CallEdge as CallEdge,
    )
    from oskill.code_parse import (
        CodeSymbol as CodeSymbol,
    )
    from oskill.code_parse import (
        CodeTree as CodeTree,
    )
    from oskill.code_parse import (
        parse_code as parse_code,
    )
    from oskill.code_parse import (
        parse_python_tree as parse_python_tree,
    )
    from oskill.coding_intelligence import (  # noqa: E402
        analyze_diff_risk as analyze_diff_risk,
    )
    from oskill.coding_intelligence import (
        analyze_symbol_impact as analyze_symbol_impact,
    )
    from oskill.coding_intelligence import (
        select_relevant_tests as select_relevant_tests,
    )
    from oskill.cold_start_single import cold_start_single as cold_start_single
    from oskill.computer_readiness import evaluate_computer_readiness as evaluate_computer_readiness
    from oskill.content_moderation import (  # noqa: E402
        ModerationRule as ModerationRule,
    )
    from oskill.content_moderation import (
        ModerationVerdict as ModerationVerdict,
    )
    from oskill.content_moderation import (
        moderate as moderate,
    )
    from oskill.content_moderation import (
        moderate_with_llm as moderate_with_llm,
    )
    from oskill.context_engineering import (  # noqa: E402
        ContextBudget as ContextBudget,
    )
    from oskill.context_engineering import (
        ContextEngine as ContextEngine,
    )
    from oskill.context_engineering import (
        ContextMessage as ContextMessage,
    )
    from oskill.context_engineering import (
        TrimResult as TrimResult,
    )
    from oskill.context_engineering import (
        compact_context as compact_context,
    )
    from oskill.context_engineering import (
        rank_context_items as rank_context_items,
    )
    from oskill.context_engineering import (
        select_context_window as select_context_window,
    )
    from oskill.conversation_vars import (  # noqa: E402
        SCOPE_PROJECT as SCOPE_PROJECT,
    )
    from oskill.conversation_vars import (
        SCOPE_SESSION as SCOPE_SESSION,
    )
    from oskill.conversation_vars import (
        ConversationVars as ConversationVars,
    )
    from oskill.conversation_vars import (
        VarEntry as VarEntry,
    )
    from oskill.daemon_runtime import (  # noqa: E402
        DaemonLifecycle as DaemonLifecycle,
    )
    from oskill.daemon_runtime import (
        DaemonState as DaemonState,
    )
    from oskill.daemon_runtime import (
        DirWatcher as DirWatcher,
    )
    from oskill.daemon_runtime import (
        SyncSession as SyncSession,
    )
    from oskill.doc_extractors import (  # noqa: E402
        DataSourceAdapter as DataSourceAdapter,
    )
    from oskill.doc_extractors import (
        extract_docx as extract_docx,
    )
    from oskill.doc_extractors import (
        extract_pdf as extract_pdf,
    )
    from oskill.doc_extractors import (
        extract_text as extract_text,
    )
    from oskill.doc_extractors import (
        extract_xlsx as extract_xlsx,
    )
    from oskill.doc_extractors import (
        fetch_url as fetch_url,
    )

    # DrawIO 非数据图示绘制 (4drawio SKILL 内化)
    from oskill.drawio_diagram import (  # noqa: E402
        STYLE_BOX as STYLE_BOX,
    )
    from oskill.drawio_diagram import (
        STYLE_DATA as STYLE_DATA,
    )
    from oskill.drawio_diagram import (
        STYLE_DECISION as STYLE_DECISION,
    )
    from oskill.drawio_diagram import (
        STYLE_EDGE as STYLE_EDGE,
    )
    from oskill.drawio_diagram import (
        STYLE_PROCESS as STYLE_PROCESS,
    )
    from oskill.drawio_diagram import (
        drawio_doc as drawio_doc,
    )
    from oskill.drawio_diagram import (
        drawio_edge as drawio_edge,
    )
    from oskill.drawio_diagram import (
        drawio_node as drawio_node,
    )
    from oskill.drawio_diagram import (
        export_drawio as export_drawio,
    )
    from oskill.drawio_diagram import (
        render_drawio as render_drawio,
    )
    from oskill.drawio_diagram import (
        validate_drawio as validate_drawio,
    )
    from oskill.embedding_service import (  # noqa: E402
        EmbeddingProvider as EmbeddingProvider,
    )
    from oskill.embedding_service import (
        EmbeddingService as EmbeddingService,
    )
    from oskill.engineering_qualification import (  # noqa: E402
        evaluate_contract as evaluate_contract,
    )
    from oskill.engineering_qualification import (
        evaluate_proven_red as evaluate_proven_red,
    )
    from oskill.engineering_qualification import (
        evaluate_ratchet as evaluate_ratchet,
    )

    # 环境检查与安装向导 (doctor SKILL 内化)
    from oskill.env_doctor import (  # noqa: E402
        DEFAULT_SPECS as DEFAULT_SPECS,
    )
    from oskill.env_doctor import (
        DepSpec as DepSpec,
    )
    from oskill.env_doctor import (
        DoctorReport as DoctorReport,
    )
    from oskill.env_doctor import (
        check_dependencies as check_dependencies,
    )
    from oskill.env_doctor import (
        detect_platform as detect_platform,
    )
    from oskill.env_doctor import (
        install_commands as install_commands,
    )
    from oskill.env_doctor import (
        run_doctor as run_doctor,
    )
    from oskill.essay_guide import essay_guide as essay_guide
    from oskill.eval_suite import (  # noqa: E402
        ComparisonReport as ComparisonReport,
    )
    from oskill.eval_suite import (
        EvalCase as EvalCase,
    )
    from oskill.eval_suite import (
        EvalRun as EvalRun,
    )
    from oskill.eval_suite import (
        Scorer as Scorer,
    )
    from oskill.eval_suite import (
        cohens_d as cohens_d,
    )
    from oskill.eval_suite import (
        compare_runs as compare_runs,
    )
    from oskill.eval_suite import (
        paired_t_test as paired_t_test,
    )
    from oskill.eval_suite import (
        run_suite as run_suite,
    )
    from oskill.eval_suite import (
        wilcoxon_signed_rank as wilcoxon_signed_rank,
    )
    from oskill.failure_learning import (  # noqa: E402
        Experience as Experience,
    )
    from oskill.failure_learning import (
        ExperienceStore as ExperienceStore,
    )
    from oskill.failure_learning import (
        FailureRecord as FailureRecord,
    )
    from oskill.failure_learning import (
        format_experiences as format_experiences,
    )

    # 科研绘图模板 (mathmodel-figure-templates SKILL 内化)
    from oskill.figure_templates import (  # noqa: E402
        list_figure_templates as list_figure_templates,
    )
    from oskill.figure_templates import (
        render_figure_template as render_figure_template,
    )
    from oskill.figure_templates import (
        resolve_template as resolve_template,
    )
    from oskill.flow_orchestrator import (  # noqa: E402
        FlowBroker as FlowBroker,
    )
    from oskill.flow_orchestrator import (
        FlowRegistry as FlowRegistry,
    )
    from oskill.flow_orchestrator import (
        FlowResult as FlowResult,
    )
    from oskill.flow_orchestrator import (
        FlowRunner as FlowRunner,
    )
    from oskill.flow_orchestrator import (
        FlowStep as FlowStep,
    )
    from oskill.fn_call_adapter import (  # noqa: E402
        adapt_call as adapt_call,
    )
    from oskill.fn_call_adapter import (
        convert_to_tool_calls as convert_to_tool_calls,
    )
    from oskill.fn_call_adapter import (
        is_function_call_output as is_function_call_output,
    )
    from oskill.fn_call_adapter import (
        mark_no_function_calling as mark_no_function_calling,
    )
    from oskill.fn_call_adapter import (
        needs_adapter as needs_adapter,
    )
    from oskill.fn_call_adapter import (
        parse_function_tags as parse_function_tags,
    )
    from oskill.fn_call_adapter import (
        tools_to_prompt as tools_to_prompt,
    )
    from oskill.fn_call_adapter import (
        wrap_tools as wrap_tools,
    )
    from oskill.health_probe import (  # noqa: E402
        STATUS_ERROR as STATUS_ERROR,
    )
    from oskill.health_probe import (
        STATUS_HEALTHY as STATUS_HEALTHY,
    )
    from oskill.health_probe import (
        STATUS_INVALID as STATUS_INVALID,
    )
    from oskill.health_probe import (
        STATUS_RATE_LIMITED as STATUS_RATE_LIMITED,
    )
    from oskill.health_probe import (
        HealthMonitor as HealthMonitor,
    )
    from oskill.health_probe import (
        HealthProbe as HealthProbe,
    )
    from oskill.health_probe import (
        ProbeState as ProbeState,
    )
    from oskill.health_score import (  # noqa: E402
        GRADE_AT_RISK as GRADE_AT_RISK,
    )
    from oskill.health_score import (
        GRADE_CRITICAL as GRADE_CRITICAL,
    )
    from oskill.health_score import (
        GRADE_HEALTHY as GRADE_HEALTHY,
    )
    from oskill.health_score import (
        LAYER_BUSINESS as LAYER_BUSINESS,
    )
    from oskill.health_score import (
        LAYER_CUSTOMER as LAYER_CUSTOMER,
    )
    from oskill.health_score import (
        LAYER_DELIVERY as LAYER_DELIVERY,
    )
    from oskill.health_score import (
        LAYER_ORG as LAYER_ORG,
    )
    from oskill.health_score import (
        LAYERS as LAYERS,
    )
    from oskill.health_score import (
        HealthAlert as HealthAlert,
    )
    from oskill.health_score import (
        HealthReport as HealthReport,
    )
    from oskill.health_score import (
        Metric as Metric,
    )
    from oskill.health_score import (
        compute_health as compute_health,
    )
    from oskill.health_score import (
        normalize as normalize,
    )
    from oskill.health_score import (
        watchdog as watchdog,
    )
    from oskill.knowledge_graph_query import (  # noqa: E402
        EDGE_EXTRACTED as EDGE_EXTRACTED,
    )
    from oskill.knowledge_graph_query import (
        EDGE_INFERRED as EDGE_INFERRED,
    )
    from oskill.knowledge_graph_query import (
        GraphEdge as GraphEdge,
    )
    from oskill.knowledge_graph_query import (
        GraphNode as GraphNode,
    )
    from oskill.knowledge_graph_query import (
        KnowledgeGraph as KnowledgeGraph,
    )
    from oskill.knowledge_graph_query import (
        semantic_to_graph as semantic_to_graph,
    )

    # LLM 智能路由技能 (RouteLLM 内化)
    from oskill.llm_router import (  # noqa: E402
        LLMRouter as LLMRouter,
    )
    from oskill.llm_router import (
        llm_router as llm_router,
    )
    from oskill.marketplace import (  # noqa: E402
        STATUS_CLAIMED as STATUS_CLAIMED,
    )
    from oskill.marketplace import (
        STATUS_DELIVERED as STATUS_DELIVERED,
    )
    from oskill.marketplace import (
        STATUS_OPEN as STATUS_OPEN,
    )
    from oskill.marketplace import (
        STATUS_SETTLED as STATUS_SETTLED,
    )
    from oskill.marketplace import (
        Listing as Listing,
    )
    from oskill.marketplace import (
        Marketplace as Marketplace,
    )
    from oskill.memory_assets import (  # noqa: E402
        ACL as ACL,
    )
    from oskill.memory_assets import (
        VISIBILITY_PRIVATE as VISIBILITY_PRIVATE,
    )
    from oskill.memory_assets import (
        VISIBILITY_RESTRICTED as VISIBILITY_RESTRICTED,
    )
    from oskill.memory_assets import (
        VISIBILITY_TEAM as VISIBILITY_TEAM,
    )
    from oskill.memory_assets import (
        AssetRegistry as AssetRegistry,
    )
    from oskill.memory_assets import (
        MemoryAsset as MemoryAsset,
    )
    from oskill.memory_assets import (
        Principal as Principal,
    )
    from oskill.memory_layers import (  # noqa: E402
        ATOM_CONSTRAINT as ATOM_CONSTRAINT,
    )
    from oskill.memory_layers import (
        ATOM_EVENT as ATOM_EVENT,
    )
    from oskill.memory_layers import (
        ATOM_FACT as ATOM_FACT,
    )
    from oskill.memory_layers import (
        ATOM_PREFERENCE as ATOM_PREFERENCE,
    )
    from oskill.memory_layers import (
        DistillPipeline as DistillPipeline,
    )
    from oskill.memory_layers import (
        L1Atom as L1Atom,
    )
    from oskill.memory_layers import (
        L2Scenario as L2Scenario,
    )
    from oskill.memory_layers import (
        L3Persona as L3Persona,
    )
    from oskill.memory_offload import (  # noqa: E402
        OffloadPipeline as OffloadPipeline,
    )
    from oskill.memory_offload import (
        TaskSegment as TaskSegment,
    )
    from oskill.memory_system import (  # noqa: E402
        MEMORY_KINDS as MEMORY_KINDS,
    )
    from oskill.memory_system import (
        MEMORY_RAG as MEMORY_RAG,
    )
    from oskill.memory_system import (
        MEMORY_TOOL as MEMORY_TOOL,
    )
    from oskill.memory_system import (
        MemoryEntry as MemoryEntry,
    )
    from oskill.memory_system import (
        MemoryStore as MemoryStore,
    )
    from oskill.memory_system import (
        ToolMemory as ToolMemory,
    )
    from oskill.metacog_scaffold import metacog_scaffold as metacog_scaffold
    from oskill.mvd import (  # noqa: E402
        PHASES as PHASES,
    )
    from oskill.mvd import (
        RULES as RULES,
    )
    from oskill.mvd import (
        MvdPipeline as MvdPipeline,
    )
    from oskill.mvd import (
        MvdVerdict as MvdVerdict,
    )
    from oskill.mvd import (
        mvd_check as mvd_check,
    )
    from oskill.pentest_loop import (  # noqa: E402
        Finding as Finding,
    )
    from oskill.pentest_loop import (
        PentestReport as PentestReport,
    )
    from oskill.pentest_loop import (
        PentestState as PentestState,
    )
    from oskill.pentest_loop import (
        run_pentest_loop as run_pentest_loop,
    )
    from oskill.pentest_loop import (
        verify_finding as verify_finding,
    )
    from oskill.pentest_squad import (  # noqa: E402
        ROLES as ROLES,
    )
    from oskill.pentest_squad import (
        SquadFinding as SquadFinding,
    )
    from oskill.pentest_squad import (
        SquadOrchestrator as SquadOrchestrator,
    )
    from oskill.pentest_squad import (
        SquadReport as SquadReport,
    )
    from oskill.playbook import (  # noqa: E402
        SECTIONS as SECTIONS,
    )
    from oskill.playbook import (
        PlaybookLibrary as PlaybookLibrary,
    )
    from oskill.playbook import (
        ScenarioPlaybook as ScenarioPlaybook,
    )
    from oskill.plugin_registry import (  # noqa: E402
        PluginDecl as PluginDecl,
    )
    from oskill.plugin_registry import (
        PluginRegistry as PluginRegistry,
    )
    from oskill.productization_gate import (  # noqa: E402
        DECISION_COMPONENTS as DECISION_COMPONENTS,
    )
    from oskill.productization_gate import (
        DECISION_KEEP_FIELD as DECISION_KEEP_FIELD,
    )
    from oskill.productization_gate import (
        DECISION_PRODUCTIZE as DECISION_PRODUCTIZE,
    )
    from oskill.productization_gate import (
        ProductizationVerdict as ProductizationVerdict,
    )
    from oskill.productization_gate import (
        evaluate_productization as evaluate_productization,
    )
    from oskill.provider_clients import (  # noqa: E402
        PROVIDER_REGISTRY as PROVIDER_REGISTRY,
    )
    from oskill.provider_clients import (
        ProviderClient as ProviderClient,
    )
    from oskill.provider_clients import (
        client_for as client_for,
    )
    from oskill.rag_pipeline import (  # noqa: E402
        Chunk as Chunk,
    )
    from oskill.rag_pipeline import (
        RagIndex as RagIndex,
    )
    from oskill.rag_pipeline import (
        build_rag_pipeline as build_rag_pipeline,
    )
    from oskill.rag_pipeline import (
        chunk_text as chunk_text,
    )
    from oskill.rag_pipeline import (
        clean_document as clean_document,
    )
    from oskill.rag_pipeline import (
        load_document as load_document,
    )
    from oskill.reflection_agent import (  # noqa: E402
        ReflectionLoop as ReflectionLoop,
    )
    from oskill.reflection_agent import (
        ReflectionResult as ReflectionResult,
    )

    # 工程工作流原语 (mattpocock skills 3O 内化)
    from oskill.requirements_interview import (  # noqa: E402
        InterviewQuestion as InterviewQuestion,
    )
    from oskill.requirements_interview import (
        InterviewState as InterviewState,
    )
    from oskill.requirements_interview import (
        interview_frontier as interview_frontier,
    )
    from oskill.requirements_interview import (
        interview_pending_facts as interview_pending_facts,
    )
    from oskill.requirements_interview import (
        interview_progress as interview_progress,
    )
    from oskill.requirements_interview import (
        is_interview_complete as is_interview_complete,
    )
    from oskill.requirements_interview import (
        record_interview_answers as record_interview_answers,
    )
    from oskill.requirements_interview import (
        record_interview_facts as record_interview_facts,
    )
    from oskill.requirements_interview import (
        resolve_interview_answer as resolve_interview_answer,
    )
    from oskill.review_double_axis import (  # noqa: E402
        ReviewFinding as ReviewFinding,
    )
    from oskill.review_double_axis import (
        ReviewReport as ReviewReport,
    )
    from oskill.review_double_axis import (
        review_diff as review_diff,
    )
    from oskill.review_double_axis import (
        scan_spec_coverage as scan_spec_coverage,
    )
    from oskill.review_double_axis import (
        scan_standards as scan_standards,
    )
    from oskill.rrf_retrieval import (  # noqa: E402
        RetrievalBudget as RetrievalBudget,
    )
    from oskill.rrf_retrieval import (
        bm25_score as bm25_score,
    )
    from oskill.rrf_retrieval import (
        hybrid_search as hybrid_search,
    )
    from oskill.rrf_retrieval import (
        rrf_merge as rrf_merge,
    )
    from oskill.rrf_retrieval import (
        tokenize as tokenize,
    )
    from oskill.rulebooks import (  # noqa: E402
        RULEBOOK_KEYWORDS as RULEBOOK_KEYWORDS,
    )
    from oskill.rulebooks import (
        get_rulebook as get_rulebook,
    )
    from oskill.rulebooks import (
        list_rulebooks as list_rulebooks,
    )
    from oskill.rulebooks import (
        rules_sections as rules_sections,
    )
    from oskill.rulebooks import (
        select_rulebooks as select_rulebooks,
    )
    from oskill.rulebooks import (
        standards_rules as standards_rules,
    )
    from oskill.runtime_backends import (  # noqa: E402
        BackendExecutor as BackendExecutor,
    )
    from oskill.runtime_backends import (
        BackendRegistry as BackendRegistry,
    )
    from oskill.runtime_backends import (
        RuntimeBackend as RuntimeBackend,
    )
    from oskill.secure_store import (  # noqa: E402
        SecureStore as SecureStore,
    )
    from oskill.secure_store import (
        SecureStoreError as SecureStoreError,
    )
    from oskill.secure_store import (
        derive_key as derive_key,
    )
    from oskill.shared_language import (  # noqa: E402
        AdrDraft as AdrDraft,
    )
    from oskill.shared_language import (
        read_glossary as read_glossary,
    )
    from oskill.shared_language import (
        should_write_adr as should_write_adr,
    )
    from oskill.shared_language import (
        upsert_term as upsert_term,
    )
    from oskill.shared_language import (
        write_adr as write_adr,
    )
    from oskill.skill_qualification import (  # noqa: E402
        compare_skill_runs as compare_skill_runs,
    )
    from oskill.skill_qualification import (
        detect_skill_regression as detect_skill_regression,
    )
    from oskill.social_publish import (  # noqa: E402
        ENV_CN as ENV_CN,
    )
    from oskill.social_publish import (
        ENV_INTL as ENV_INTL,
    )
    from oskill.social_publish import (
        PLATFORM_TIKTOK as PLATFORM_TIKTOK,
    )
    from oskill.social_publish import (
        PLATFORM_WECHAT as PLATFORM_WECHAT,
    )
    from oskill.social_publish import (
        PLATFORM_XIAOHONGSHU as PLATFORM_XIAOHONGSHU,
    )
    from oskill.social_publish import (
        PLATFORM_YOUTUBE as PLATFORM_YOUTUBE,
    )
    from oskill.social_publish import (
        SETTLEMENT_FIXED as SETTLEMENT_FIXED,
    )
    from oskill.social_publish import (
        SETTLEMENT_PER_UNIT as SETTLEMENT_PER_UNIT,
    )
    from oskill.social_publish import (
        SETTLEMENT_REVENUE_SHARE as SETTLEMENT_REVENUE_SHARE,
    )
    from oskill.social_publish import (
        GenericHttpAdapter as GenericHttpAdapter,
    )
    from oskill.social_publish import (
        PlatformAdapter as PlatformAdapter,
    )
    from oskill.social_publish import (
        PlatformCapabilities as PlatformCapabilities,
    )
    from oskill.social_publish import (
        PlatformCredential as PlatformCredential,
    )
    from oskill.social_publish import (
        PublishResult as PublishResult,
    )
    from oskill.social_publish import (
        SocialTask as SocialTask,
    )
    from oskill.social_publish import (
        WechatAdapter as WechatAdapter,
    )
    from oskill.social_publish import (
        batch_draft as batch_draft,
    )
    from oskill.social_publish import (
        content_limits as content_limits,
    )
    from oskill.social_publish import (
        get_platform as get_platform,
    )
    from oskill.social_publish import (
        list_platforms as list_platforms,
    )
    from oskill.social_publish import (
        mark_settled as mark_settled,
    )
    from oskill.social_publish import (
        publish_to as publish_to,
    )
    from oskill.social_publish import (
        register_platform as register_platform,
    )
    from oskill.social_publish import (
        settle as settle,
    )
    from oskill.socratic_guide_v2 import (
        SocraticStateV2 as SocraticStateV2,
    )
    from oskill.socratic_guide_v2 import (
        socratic_guide_v2 as socratic_guide_v2,
    )

    # 可执行 Spec 技能 (spec-kit 内化) + ECC 领域分派基础
    from oskill.spec_execute import (  # noqa: E402
        PRESETS as PRESETS,
    )
    from oskill.spec_execute import (
        SpecExecutor as SpecExecutor,
    )
    from oskill.spec_execute import (
        render_preset as render_preset,
    )
    from oskill.spec_execute import (
        spec_executor as spec_executor,
    )
    from oskill.svg_craft import (  # noqa: E402
        LEVEL_NAMES as LEVEL_NAMES,
    )
    from oskill.svg_craft import (
        GateVerdict as GateVerdict,
    )
    from oskill.svg_craft import (
        LadderDecision as LadderDecision,
    )
    from oskill.svg_craft import (
        PathAudit as PathAudit,
    )
    from oskill.svg_craft import (
        PathSegment as PathSegment,
    )
    from oskill.svg_craft import (
        complexity_ladder as complexity_ladder,
    )
    from oskill.svg_craft import (
        iou_score as iou_score,
    )
    from oskill.svg_craft import (
        parse_path as parse_path,
    )
    from oskill.svg_craft import (
        smoothness_gate as smoothness_gate,
    )
    from oskill.svg_craft import (
        svg_path_audit as svg_path_audit,
    )
    from oskill.svg_path_tools import (  # noqa: E402
        fit_smooth_cubic as fit_smooth_cubic,
    )
    from oskill.svg_path_tools import (
        path_bbox as path_bbox,
    )
    from oskill.svg_path_tools import (
        path_center as path_center,
    )
    from oskill.svg_path_tools import (
        render_cubic_path as render_cubic_path,
    )
    from oskill.svg_path_tools import (
        simplify_line as simplify_line,
    )
    from oskill.template_engine import (  # noqa: E402
        extract_variables as extract_variables,
    )
    from oskill.template_engine import (
        render_template as render_template,
    )
    from oskill.test_report import (  # noqa: E402
        TestCaseResult as TestCaseResult,
    )
    from oskill.test_report import (
        TestRunReport as TestRunReport,
    )
    from oskill.test_report import (
        collect_test_run as collect_test_run,
    )
    from oskill.test_stability import (  # noqa: E402
        ACTIONABLE_ANIMATION_STABLE as ACTIONABLE_ANIMATION_STABLE,
    )
    from oskill.test_stability import (
        ACTIONABLE_CHECKS as ACTIONABLE_CHECKS,
    )
    from oskill.test_stability import (
        ACTIONABLE_CLICKABLE as ACTIONABLE_CLICKABLE,
    )
    from oskill.test_stability import (
        ACTIONABLE_NOT_COVERED as ACTIONABLE_NOT_COVERED,
    )
    from oskill.test_stability import (
        ACTIONABLE_VISIBLE as ACTIONABLE_VISIBLE,
    )
    from oskill.test_stability import (
        RunResult as RunResult,
    )
    from oskill.test_stability import (
        expect_eventually as expect_eventually,
    )
    from oskill.test_stability import (
        retry_until as retry_until,
    )
    from oskill.test_stability import (
        wait_actionable as wait_actionable,
    )
    from oskill.triage_flow import (  # noqa: E402
        STATUS_NEEDS_INFO as STATUS_NEEDS_INFO,
    )
    from oskill.triage_flow import (
        STATUS_NEEDS_TRIAGE as STATUS_NEEDS_TRIAGE,
    )
    from oskill.triage_flow import (
        STATUS_READY_AGENT as STATUS_READY_AGENT,
    )
    from oskill.triage_flow import (
        STATUS_READY_HUMAN as STATUS_READY_HUMAN,
    )
    from oskill.triage_flow import (
        STATUS_WONTFIX as STATUS_WONTFIX,
    )
    from oskill.triage_flow import (
        TriageFlow as TriageFlow,
    )
    from oskill.triage_flow import (
        TriageIssue as TriageIssue,
    )

    # Typst 撰写技能 (typst-author SKILL 内化)
    from oskill.typst_author import (  # noqa: E402
        TYPST_GUIDE as TYPST_GUIDE,
    )
    from oskill.typst_author import (
        typst_compile as typst_compile,
    )
    from oskill.typst_author import (
        typst_format_check as typst_format_check,
    )
    from oskill.typst_author import (
        typst_minimal_doc as typst_minimal_doc,
    )
    from oskill.typst_author import (
        typst_probe as typst_probe,
    )
    from oskill.variant_for_review import variant_for_review as variant_for_review

    # 论文验收与一致性检查 (6verity SKILL 内化)
    from oskill.verity_check import (  # noqa: E402
        PLACEHOLDER_RE as PLACEHOLDER_RE,
    )
    from oskill.verity_check import (
        VerityConfig as VerityConfig,
    )
    from oskill.verity_check import (
        VerityItem as VerityItem,
    )
    from oskill.verity_check import (
        VerityReport as VerityReport,
    )
    from oskill.verity_check import (
        compile_paper as compile_paper,
    )
    from oskill.verity_check import (
        pdf_pages as pdf_pages,
    )
    from oskill.verity_check import (
        resolve_config as resolve_config,
    )
    from oskill.verity_check import (
        run_text_gate as run_text_gate,
    )
    from oskill.verity_check import (
        run_verity as run_verity,
    )
    from oskill.voice_pipeline import (  # noqa: E402
        FULL_DUPLEX_MODE as FULL_DUPLEX_MODE,
    )
    from oskill.voice_pipeline import (
        PIPE_MODE as PIPE_MODE,
    )
    from oskill.voice_pipeline import (
        STREAM_MODE as STREAM_MODE,
    )
    from oskill.voice_pipeline import (
        VoiceTurn as VoiceTurn,
    )
    from oskill.voice_pipeline import (
        interrupt_turn as interrupt_turn,
    )
    from oskill.voice_pipeline import (
        run_voice_pipeline as run_voice_pipeline,
    )
    from oskill.wechat_publish import (  # noqa: E402
        Article as Article,
    )
    from oskill.wechat_publish import (
        ArticleStore as ArticleStore,
    )
    from oskill.wechat_publish import (
        WechatAccount as WechatAccount,
    )
    from oskill.wechat_publish import (
        WechatAccountRegistry as WechatAccountRegistry,
    )
    from oskill.wechat_publish import (
        create_image_post as create_image_post,
    )
    from oskill.wechat_publish import (
        inspect_article as inspect_article,
    )
    from oskill.wechat_publish import (
        md_to_wechat_html as md_to_wechat_html,
    )
    from oskill.wechat_publish import (
        produce_article as produce_article,
    )
    from oskill.wechat_publish import (
        publish_draft as publish_draft,
    )
    from oskill.wechat_publish import (
        upload_image as upload_image,
    )
    from oskill.wechat_resources import (  # noqa: E402
        catalog_summary as catalog_summary,
    )
    from oskill.wechat_resources import (
        register_wechat_resources as register_wechat_resources,
    )
    from oskill.wechat_resources import (
        wechat_catalog as wechat_catalog,
    )
    from oskill.wechat_review_loop import (  # noqa: E402
        FULL_REWRITE_CRITERIA as FULL_REWRITE_CRITERIA,
    )
    from oskill.wechat_review_loop import (
        ReviewIssue as ReviewIssue,
    )
    from oskill.wechat_review_loop import (
        ReviewRound as ReviewRound,
    )
    from oskill.wechat_review_loop import (
        WechatReviewLoop as WechatReviewLoop,
    )
    from oskill.wechat_review_loop import (
        merge_revision as merge_revision,
    )
    from oskill.wechat_review_loop import (
        needs_full_rewrite as needs_full_rewrite,
    )
    from oskill.wechat_review_loop import (
        parse_verdict as parse_verdict,
    )
    from oskill.wechat_theme import (  # noqa: E402
        LayoutBlock as LayoutBlock,
    )
    from oskill.wechat_theme import (
        WechatTheme as WechatTheme,
    )
    from oskill.wechat_theme import (
        apply_theme as apply_theme,
    )
    from oskill.wechat_theme import (
        get_theme as get_theme,
    )
    from oskill.wechat_theme import (
        layout_modules as layout_modules,
    )
    from oskill.wechat_theme import (
        list_themes as list_themes,
    )
    from oskill.wechat_theme import (
        parse_layout_blocks as parse_layout_blocks,
    )
    from oskill.wechat_theme import (
        register_layout_module as register_layout_module,
    )
    from oskill.wechat_theme import (
        register_theme as register_theme,
    )
    from oskill.wechat_theme import (
        render_layout_block as render_layout_block,
    )
    from oskill.wechat_theme import (
        render_markdown_with_layout as render_markdown_with_layout,
    )
    from oskill.wechat_writing import (  # noqa: E402
        ComplianceHit as ComplianceHit,
    )
    from oskill.wechat_writing import (
        advise_prompt as advise_prompt,
    )
    from oskill.wechat_writing import (
        compliance_report as compliance_report,
    )
    from oskill.wechat_writing import (
        cover_prompt as cover_prompt,
    )
    from oskill.wechat_writing import (
        humanize_prompt as humanize_prompt,
    )
    from oskill.wechat_writing import (
        infographic_prompt as infographic_prompt,
    )
    from oskill.wechat_writing import (
        reviewer_prompt as reviewer_prompt,
    )
    from oskill.wechat_writing import (
        reviser_prompt as reviser_prompt,
    )
    from oskill.wechat_writing import (
        scan_compliance as scan_compliance,
    )
    from oskill.wechat_writing import (
        title_prompt as title_prompt,
    )
    from oskill.wechat_writing import (
        write_prompt as write_prompt,
    )
    from oskill.workflow_dsl import (  # noqa: E402
        NODE_CONDITION as NODE_CONDITION,
    )
    from oskill.workflow_dsl import (
        NODE_END as NODE_END,
    )
    from oskill.workflow_dsl import (
        NODE_ITERATION as NODE_ITERATION,
    )
    from oskill.workflow_dsl import (
        NODE_KNOWLEDGE as NODE_KNOWLEDGE,
    )
    from oskill.workflow_dsl import (
        NODE_LLM as NODE_LLM,
    )
    from oskill.workflow_dsl import (
        NODE_START as NODE_START,
    )
    from oskill.workflow_dsl import (
        NODE_TOOL as NODE_TOOL,
    )
    from oskill.workflow_dsl import (
        NODE_VARIABLE as NODE_VARIABLE,
    )
    from oskill.workflow_dsl import (
        WorkflowDAG as WorkflowDAG,
    )
    from oskill.workflow_dsl import (
        WorkflowNode as WorkflowNode,
    )
    from oskill.workflow_dsl import (
        parse_dsl as parse_dsl,
    )
    from oskill.workflow_dsl import (
        parse_dsl_json as parse_dsl_json,
    )
    from oskill.workflow_dsl import (
        topological_execute as topological_execute,
    )
    from oskill.workflow_dsl import (
        validate_dsl as validate_dsl,
    )
    from oskill.workflow_pipeline import (  # noqa: E402
        TICKET_BLOCKED as TICKET_BLOCKED,
    )
    from oskill.workflow_pipeline import (
        TICKET_DONE as TICKET_DONE,
    )
    from oskill.workflow_pipeline import (
        TICKET_OPEN as TICKET_OPEN,
    )
    from oskill.workflow_pipeline import (
        PipelineAction as PipelineAction,
    )
    from oskill.workflow_pipeline import (
        Ticket as Ticket,
    )
    from oskill.workflow_pipeline import (
        WorkflowState as WorkflowState,
    )
    from oskill.workflow_pipeline import (
        pipeline_next_action as pipeline_next_action,
    )
    from oskill.workflow_pipeline import (
        pipeline_transition as pipeline_transition,
    )
    from oskill.workflow_pipeline import (
        ticket_set_status as ticket_set_status,
    )
    from oskill.workflow_pipeline import (
        tickets_check_cycles as tickets_check_cycles,
    )
    from oskill.workflow_pipeline import (
        tickets_next_runnable as tickets_next_runnable,
    )
    from oskill.workflow_pipeline import (
        workflow_from_dict as workflow_from_dict,
    )
    from oskill.workflow_pipeline import (
        workflow_to_dict as workflow_to_dict,
    )

    # ── Phase 2: 贝叶斯 ToM 信念更新 ───────────────────────────────────
    from ._bayesian_belief_update import (  # noqa: F401
        DEFAULT_HYPOTHESES as DEFAULT_HYPOTHESES,
    )
    from ._bayesian_belief_update import (
        BayesianBeliefUpdater as BayesianBeliefUpdater,
    )
    from ._bayesian_belief_update import (
        _bayesian_belief_update as _bayesian_belief_update,
    )
    from ._bayesian_belief_update import (
        sequential_update as sequential_update,
    )

    # ── Phase 3: 在线因果参数更新 (CPD, Dirichlet/EMA) ──────────────────
    from ._online_cpd_update import (  # noqa: F401
        CategoricalCPD as CategoricalCPD,
    )
    from ._online_cpd_update import (
        config_key as config_key,
    )
    from ._online_cpd_update import (
        dirichlet_update as dirichlet_update,
    )
    from ._online_cpd_update import (
        ema_update as ema_update,
    )
    from ._online_cpd_update import (
        split_config as split_config,
    )
    from ._online_cpd_update import (
        update_cpd as update_cpd,
    )

    # ── Phase 4: 长期策略演化 ────────────────────────────────────────────
    from ._strategy_evolve import (  # noqa: F401
        STRATEGY_NAMES as STRATEGY_NAMES,
    )
    from ._strategy_evolve import (
        STRATEGY_PARAMS as STRATEGY_PARAMS,
    )
    from ._strategy_evolve import (
        StrategyEvolver as StrategyEvolver,
    )

    # AutoAgent capability imports
    from .agent_form_synthesize import agent_form_synthesize as agent_form_synthesize  # noqa: F401

    # PR-12 stateless execution-layer skills. Pin the functions explicitly so
    # package imports do not resolve to same-named lazy submodules.
    from .aggregate_usage import aggregate_usage as aggregate_usage  # noqa: F401

    # PR-13 stateless tool/MCP governance skills.
    from .classify_tool_effect import classify_tool_effect as classify_tool_effect  # noqa: F401
    from .dag_visual_layout import dag_visual_layout as dag_visual_layout  # noqa: F401
    from .deep_research_tree import deep_research_tree as deep_research_tree  # noqa: F401
    from .fallback_decision import fallback_decision as fallback_decision  # noqa: F401
    from .leader_worker_dispatch import (
        leader_worker_dispatch as leader_worker_dispatch,  # noqa: F401
    )
    from .meta_self_develop_loop import (
        meta_self_develop_loop as meta_self_develop_loop,  # noqa: F401
    )
    from .prepare_tool_execution import (
        prepare_tool_execution as prepare_tool_execution,  # noqa: F401
    )
    from .recurring_scheduler import RecurringScheduler as RecurringScheduler  # noqa: F401
    from .resolve_tool_grant import resolve_tool_grant as resolve_tool_grant  # noqa: F401
    from .scheduler_attempt_lifecycle import (  # noqa: F401
        monthly_clamp as monthly_clamp,
    )
    from .scheduler_attempt_lifecycle import (
        pre_run_knowledge_hook as pre_run_knowledge_hook,
    )
    from .scheduler_attempt_lifecycle import (
        retry_execute as retry_execute,
    )
    from .scheduler_attempt_lifecycle import (
        transition_attempt as transition_attempt,
    )
    from .select_provider import select_provider as select_provider  # noqa: F401
    from .skill_teach import (
        skill_export as skill_export,
    )  # noqa: F401
    from .skill_teach import (
        skill_import_ as skill_import_,
    )
    from .skill_teach import (
        skill_list as skill_list,
    )
    from .skill_teach import (
        skill_teach as skill_teach,
    )
    from .skills_dynamic_inject import skills_dynamic_inject as skills_dynamic_inject  # noqa: F401
    from .soul_self_evolution import soul_self_evolution as soul_self_evolution  # noqa: F401
    from .team_plan_gen import team_plan_gen as team_plan_gen  # noqa: F401
    from .worktree_conflict_resolve import (
        worktree_conflict_resolve as worktree_conflict_resolve,  # noqa: F401
    )
