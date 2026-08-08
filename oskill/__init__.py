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
                        # Heuristic: prefer non-prefixed modules, or if mapping to private, allow overwrite by public
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
from oskill._allocate_gift_card_balance import allocate_gift_card_balance
from oskill._apply_discount_amount import apply_discount_amount
from oskill._apply_discount_percentage import apply_discount_percentage
from oskill._apply_edit_block import apply_edit_block
from oskill._apply_free_shipping import apply_free_shipping
from oskill._apply_todo_update import apply_todo_update
from oskill._apply_unified_diff import apply_unified_diff
from oskill._build_repo_context import build_repo_context
from oskill._build_subagent_prompt import build_subagent_prompt
from oskill._build_undo_plan import build_undo_plan

# K-G5: safe cascade delete (dry_run=True default; shared KUs preserved)
from oskill._cascade_delete import cascade_delete
from oskill._chunk_code import chunk_code
from oskill._compose_plugin_manifest import compose_plugin_manifest
from oskill._compress_context import compress_context
from oskill._compute_cart_grand_total import compute_cart_grand_total
from oskill._compute_cart_subtotal import compute_cart_subtotal

# ── AII Graph Capability (K-G1 … K-G5) ──────────────────────────────────────
# K-G1: LLM-confirmed conflict resolution (grade hardcoded unverified)
from oskill._conflict_resolution import conflict_resolution
from oskill._dedup_edits import dedup_edits
from oskill._escalate_thinking_budget import escalate_thinking_budget
from oskill._evaluate_discount_conditions import evaluate_discount_conditions
from oskill._evaluate_discount_eligibility import evaluate_discount_eligibility
from oskill._evaluate_hooks import evaluate_hooks
from oskill._extract_symbols import extract_symbols
from oskill._format_diagnostics import format_diagnostics
from oskill._generate_patch_preview import generate_patch_preview

# K-G4: BFS graph expansion with relevance pruning
from oskill._graph_expand_retrieval import graph_expand_retrieval
from oskill._load_skill_progressive import load_skill_progressive
from oskill._match_permission_rule import match_permission_rule
from oskill._merge_config import merge_config
from oskill._merge_subagent_result import merge_subagent_result
from oskill._parse_llm_tool_calls import parse_llm_tool_calls
from oskill._physics_force_analysis_guide import ForceAnalysisResult, physics_force_analysis_guide
from oskill._plan_decompose import plan_decompose
from oskill._plan_to_todos import plan_to_todos
from oskill._rank_relevant_files import rank_relevant_files
from oskill._reading_comprehension_guide import ReadingGuideResult, reading_comprehension_guide

# K-G3: composite KU relevance scoring (direct/source/adamic/type weights)
from oskill._relevance_compute import relevance_compute
from oskill._repo_map_build import repo_map_build

# ── Batch-warehouse commerce vertical ───────────────────────────────────────
from oskill._resolve_display_batch import resolve_display_batch
from oskill._resolve_memory_hierarchy import resolve_memory_hierarchy
from oskill._resolve_mentions import resolve_mentions
from oskill._select_skill import select_skill
from oskill._select_tools import select_tools
from oskill._semantic_search import semantic_search
from oskill._stack_discount_allocations import stack_discount_allocations
from oskill._summarize_file import summarize_file
from oskill._syntax_check import syntax_check
from oskill._three_way_merge import three_way_merge

# K-G2: two-pass CoT knowledge extraction (analyze → generate, no free-play)
from oskill._two_step_ingest import two_step_ingest
from oskill._types import (
    ApplyResult,
    Chunk,
    ConfigOskillError,
    EditBlock,
    EditOskillError,
    HookCmd,
    LLMOskillError,
    OskillError,
    ParseOskillError,
    PluginManifest,
    RepoFile,
    RepoMap,
    SubTask,
    Symbol,
    TodoItem,
    ToolCall,
    UndoPlan,
)
from oskill._validate_edit import validate_edit
from oskill.cold_start_single import cold_start_single

# DrawIO 非数据图示绘制 (4drawio SKILL 内化)
from oskill.drawio_diagram import (  # noqa: E402
    STYLE_BOX,
    STYLE_DATA,
    STYLE_DECISION,
    STYLE_EDGE,
    STYLE_PROCESS,
    drawio_doc,
    drawio_edge,
    drawio_node,
    export_drawio,
    render_drawio,
    validate_drawio,
)

# 环境检查与安装向导 (doctor SKILL 内化)
from oskill.env_doctor import (  # noqa: E402
    DEFAULT_SPECS,
    DepSpec,
    DoctorReport,
    check_dependencies,
    detect_platform,
    install_commands,
    run_doctor,
)
from oskill.essay_guide import essay_guide

# 科研绘图模板 (mathmodel-figure-templates SKILL 内化)
from oskill.figure_templates import (  # noqa: E402
    list_figure_templates,
    render_figure_template,
    resolve_template,
)

# LLM 智能路由技能 (RouteLLM 内化)
from oskill.llm_router import (  # noqa: E402
    LLMRouter,
    llm_router,
)
from oskill.metacog_scaffold import metacog_scaffold

# 工程工作流原语 (mattpocock skills 3O 内化)
from oskill.requirements_interview import (  # noqa: E402
    InterviewQuestion,
    InterviewState,
    interview_frontier,
    interview_pending_facts,
    interview_progress,
    is_interview_complete,
    record_interview_answers,
    record_interview_facts,
    resolve_interview_answer,
)
from oskill.review_double_axis import (  # noqa: E402
    ReviewFinding,
    ReviewReport,
    review_diff,
    scan_spec_coverage,
    scan_standards,
)
from oskill.shared_language import (  # noqa: E402
    AdrDraft,
    read_glossary,
    should_write_adr,
    upsert_term,
    write_adr,
)
from oskill.socratic_guide_v2 import SocraticStateV2, socratic_guide_v2

# 可执行 Spec 技能 (spec-kit 内化) + ECC 领域分派基础
from oskill.spec_execute import (  # noqa: E402
    PRESETS,
    SpecExecutor,
    render_preset,
    spec_executor,
)

# Typst 撰写技能 (typst-author SKILL 内化)
from oskill.typst_author import (  # noqa: E402
    TYPST_GUIDE,
    typst_compile,
    typst_format_check,
    typst_minimal_doc,
    typst_probe,
)
from oskill.variant_for_review import variant_for_review

# 论文验收与一致性检查 (6verity SKILL 内化)
from oskill.verity_check import (  # noqa: E402
    PLACEHOLDER_RE,
    VerityConfig,
    VerityItem,
    VerityReport,
    compile_paper,
    pdf_pages,
    resolve_config,
    run_text_gate,
    run_verity,
)
from oskill.code_graph_semantic import (  # noqa: E402
    LINK_DEPENDS_ON,
    LINK_IMPLEMENTS,
    LINK_PART_OF,
    LINK_PRODUCES,
    LINK_USES,
    SemanticBuild,
    SemanticNode,
    SourceRef,
    build_fingerprint,
    content_hash,
    incremental_refresh,
    parse_wikilinks,
    render_node_markdown,
    semantic_build,
    stale_nodes,
)
from oskill.agent_wiring import (  # noqa: E402
    WiringResult,
    list_agents,
    plan_wiring,
    write_agent_instructions,
)
from oskill.agent_discovery import (  # noqa: E402
    AntiNoiseValidator,
    DecisionVerdict,
    Resource,
    ResourceCatalog,
)
from oskill.wechat_publish import (  # noqa: E402
    Article,
    ArticleStore,
    md_to_wechat_html,
    produce_article,
    publish_draft,
)
from oskill.eval_suite import (  # noqa: E402
    ComparisonReport,
    EvalCase,
    EvalRun,
    Scorer,
    compare_runs,
    cohens_d,
    paired_t_test,
    run_suite,
    wilcoxon_signed_rank,
)
from oskill.failure_learning import (  # noqa: E402
    Experience,
    ExperienceStore,
    FailureRecord,
    format_experiences,
)
from oskill.agent_context_pool import (  # noqa: E402
    ContextItem,
    ContextPool,
    VISIBILITY_DERIVED,
    VISIBILITY_ISOLATED,
    VISIBILITY_SHARED,
)
from oskill.voice_pipeline import (  # noqa: E402
    PIPE_MODE,
    STREAM_MODE,
    FULL_DUPLEX_MODE,
    VoiceTurn,
    interrupt_turn,
    run_voice_pipeline,
)
from oskill.rulebooks import (  # noqa: E402
    RULEBOOK_KEYWORDS,
    get_rulebook,
    list_rulebooks,
    rules_sections,
    select_rulebooks,
    standards_rules,
)
from oskill.workflow_pipeline import (  # noqa: E402
    TICKET_BLOCKED,
    TICKET_DONE,
    TICKET_OPEN,
    PipelineAction,
    Ticket,
    WorkflowState,
    pipeline_next_action,
    pipeline_transition,
    ticket_set_status,
    tickets_check_cycles,
    tickets_next_runnable,
    workflow_from_dict,
    workflow_to_dict,
)

# ── Phase 2: 贝叶斯 ToM 信念更新 ───────────────────────────────────
from ._bayesian_belief_update import (  # noqa: F401
    DEFAULT_HYPOTHESES,
    BayesianBeliefUpdater,
    _bayesian_belief_update,
    sequential_update,
)

# ── Phase 3: 在线因果参数更新 (CPD, Dirichlet/EMA) ──────────────────
from ._online_cpd_update import (  # noqa: F401
    CategoricalCPD,
    config_key,
    dirichlet_update,
    ema_update,
    split_config,
    update_cpd,
)

# ── Phase 4: 长期策略演化 ────────────────────────────────────────────
from ._strategy_evolve import (  # noqa: F401
    STRATEGY_NAMES,
    STRATEGY_PARAMS,
    StrategyEvolver,
)

# AutoAgent capability imports
from .agent_form_synthesize import agent_form_synthesize  # noqa: F401
from .dag_visual_layout import dag_visual_layout  # noqa: F401
from .deep_research_tree import deep_research_tree  # noqa: F401
from .leader_worker_dispatch import leader_worker_dispatch  # noqa: F401
from .meta_self_develop_loop import meta_self_develop_loop  # noqa: F401
from .recurring_scheduler import RecurringScheduler  # noqa: F401
from .scheduler_attempt_lifecycle import (  # noqa: F401
    monthly_clamp,
    pre_run_knowledge_hook,
    retry_execute,
    transition_attempt,
)
from .skill_teach import skill_export, skill_import_, skill_list, skill_teach  # noqa: F401
from .skills_dynamic_inject import skills_dynamic_inject  # noqa: F401
from .soul_self_evolution import soul_self_evolution  # noqa: F401
from .team_plan_gen import team_plan_gen  # noqa: F401
from .worktree_conflict_resolve import worktree_conflict_resolve  # noqa: F401
