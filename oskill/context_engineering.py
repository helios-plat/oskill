"""oskill.context_engineering — 上下文工程 (hello-agents 第9章 3O 内化)。

持续交互的上下文管理 (veya context.py 的机制层):
  * **ContextMessage** — 消息 (role/content/priority/timestamp/summary);
  * **ContextBudget** — 预算 (token/字符上限, 超限策略);
  * **trim** — 裁剪: 按优先级保留 + 摘要化低优先级 + 截断;
  * **summarize_old** — 旧消息摘要压缩 (LLM 注入或规则);
  * 与 memory_layers/memory_hub 组合 (上下文窗口管理)。
零 veya 反向依赖: 摘要函数注入; token 计数注入 (默认 len/4)。
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from oprim import count_tokens, truncate_for_context

ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


@dataclass
class ContextMessage:
    """一条上下文消息 (带优先级/时间)。"""

    role: str
    content: str
    priority: int = 1  # 高优先级 = 保留 (0 最优先)
    ts: float = 0.0
    summary: str | None = None  # 摘要化后内容

    def effective_content(self) -> str:
        return self.summary if self.summary is not None else self.content


TokenCounter = Callable[[str], int]
"""token 计数: (text) → token 数。"""


@runtime_checkable
class CodeKnowledgeGraphPort(Protocol):
    """Structural retrieval port; the context engine does not import the graph."""

    async def context_slice(self, symbol: Any, **kwargs: Any) -> Any: ...

    async def impact(self, symbol: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class ObservationJournalPort(Protocol):
    """Observation retrieval port; observations are not treated as evidence."""

    async def query(self, **kwargs: Any) -> Sequence[Any]: ...


@runtime_checkable
class SkillDisclosurePort(Protocol):
    """Progressive-disclosure port for a skill distribution provider."""

    async def resolve(self, ref: Any, *, level: int = 1, **kwargs: Any) -> Any: ...


def _default_token_counter(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class ContextBudget:
    """上下文预算。"""

    max_tokens: int = 8000
    keep_roles: tuple[str, ...] = (ROLE_SYSTEM,)
    summarize_below_priority: int = 2  # 低于该优先级 → 可摘要

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "keep_roles": self.keep_roles,
            "summarize_below_priority": self.summarize_below_priority,
        }


@dataclass
class TrimResult:
    """裁剪结果。"""

    messages: list[ContextMessage]
    total_tokens: int
    summarized: int = 0
    dropped: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "summarized": self.summarized,
            "dropped": self.dropped,
            "count": len(self.messages),
        }


class ContextEngine:
    """上下文工程: 管理消息窗口 (优先级/摘要/裁剪)。"""

    CONTEXTENGINE_AUTHORITY = 0

    def __init__(self, *, token_counter: TokenCounter | None = None) -> None:
        self.token_counter = token_counter or _default_token_counter

    def trim(
        self,
        messages: list[ContextMessage],
        budget: ContextBudget,
        *,
        summarize_fn: Callable[[str], str] | None = None,
    ) -> TrimResult:
        """裁剪消息窗口到预算内。

        策略 (确定性):
        1. 必须保留 role ∈ keep_roles (如 system);
        2. 低优先级 (priority >= summarize_below_priority) 且非必须 → 摘要化;
        3. 仍超限 → 从低优先级丢弃 (保留最新);
        4. 高优先级可截断内容到预算。

        Args:
            messages: 消息 (按时间序)。
            budget: 预算。
            summarize_fn: 摘要函数 (None 时低优先级直接丢弃)。

        Returns:
            TrimResult。
        """
        summarized = 0
        dropped = 0

        def token_count(m: ContextMessage) -> int:
            return self.token_counter(m.effective_content())

        # 1. 必须保留的 (system 等)
        must_keep = [m for m in messages if m.role in budget.keep_roles]
        others = [m for m in messages if m.role not in budget.keep_roles]
        must_tokens = sum(token_count(m) for m in must_keep)
        others.sort(key=lambda m: (m.priority, -m.ts))  # 低优先级在前, 旧在前

        # 2. 摘要化低优先级 (从最旧开始)
        if summarize_fn is not None:
            candidates = [
                m
                for m in others
                if m.priority >= budget.summarize_below_priority and m.summary is None
            ]
            for m in candidates:
                m.summary = summarize_fn(m.content)[:400]
                summarized += 1

        # 3-4. 逐步丢弃/截断
        kept: list[ContextMessage] = list(must_keep)
        total = must_tokens
        for m in sorted(others, key=lambda m: (m.priority, m.ts)):
            if m.summary is not None:
                kept.append(m)
                total += token_count(m)
            else:
                kept.append(m)
                total += token_count(m)
        # 超限: 从非必须中丢弃最旧的
        non_keep_indices = [i for i, m in enumerate(kept) if m.role not in budget.keep_roles]
        while total > budget.max_tokens and non_keep_indices:
            idx = non_keep_indices.pop(0)  # 最旧非必须
            removed = kept.pop(idx)
            total -= token_count(removed)
            dropped += 1
            non_keep_indices = [i for i, m in enumerate(kept) if m.role not in budget.keep_roles]
        # 仍超限: 截断最后一条
        if total > budget.max_tokens and kept:
            last = kept[-1]
            overflow = total - budget.max_tokens
            trimmed_content = last.effective_content()[: -overflow * 4]
            last.summary = trimmed_content + "…"
            total = must_tokens + sum(self.token_counter(m.effective_content()) for m in kept)
        return TrimResult(messages=kept, total_tokens=total, summarized=summarized, dropped=dropped)

    async def retrieve_code_context(
        self,
        graph: CodeKnowledgeGraphPort,
        symbol: Any,
        *,
        token_budget: int = 2000,
        max_depth: int = 2,
        repo_id: str | None = None,
        revision: str | None = None,
        include_impact: bool = True,
    ) -> dict[str, Any]:
        """Adapt graph facts into bounded context items.

        The graph remains a fact provider.  This method only serializes and
        budgets its output; it does not decide a code change or acceptance.
        """
        context_slice = await graph.context_slice(
            symbol,
            token_budget=token_budget,
            max_depth=max_depth,
            repo_id=repo_id,
            revision=revision,
        )
        impact = None
        if include_impact:
            impact = await graph.impact(
                symbol,
                max_depth=max_depth,
                repo_id=repo_id,
                revision=revision,
            )
        slice_data = _as_serializable(context_slice)
        impact_data = _as_serializable(impact) if impact is not None else None
        content = json.dumps(
            {"code_context": slice_data, "code_impact": impact_data},
            ensure_ascii=False,
            sort_keys=True,
        )
        selected = select_context_window(
            ranked_items=[
                {
                    "source": "code_knowledge_graph",
                    "kind": "code_context",
                    "content": content,
                    "importance": 1.0,
                    "source_quality": 1.0,
                }
            ],
            token_budget=token_budget,
        )
        return {
            "items": selected["selected_items"],
            "used_tokens": selected["used_tokens"],
            "token_budget": token_budget,
            "impact": impact_data,
            "authority": 0,
        }

    async def retrieve_observation_context(
        self,
        journal: ObservationJournalPort,
        query: Mapping[str, Any] | Any,
        *,
        token_budget: int = 2000,
    ) -> dict[str, Any]:
        """Retrieve observations as provenance-labelled context, never evidence."""
        if isinstance(query, Mapping):
            observations = await journal.query(**dict(query))
        else:
            observations = await journal.query(query=query)
        items = [
            {
                "source": "observation_journal",
                "kind": "observation",
                "content": json.dumps(_as_serializable(item), ensure_ascii=False, sort_keys=True),
                "importance": 0.5,
                "source_quality": 0.5,
                "observation": _as_serializable(item),
            }
            for item in observations
        ]
        ranked = self.score_sources(items, query=query)
        selected = select_context_window(
            ranked_items=ranked["ranked_items"], token_budget=token_budget
        )
        return {
            "items": selected["selected_items"],
            "used_tokens": selected["used_tokens"],
            "token_budget": token_budget,
            "observation_not_evidence": True,
            "authority": 0,
        }

    async def progressive_disclosure(
        self,
        provider: SkillDisclosurePort,
        ref: Any,
        *,
        level: int = 1,
        token_budget: int = 4000,
        business_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load only the requested skill disclosure level and budget it."""
        if level < 0 or level > 3:
            raise ValueError("disclosure level must be between 0 and 3")
        bundle = await provider.resolve(ref, level=level, business_context=business_context)
        data = _as_serializable(bundle)
        descriptor = data.get("descriptor", data)
        items: list[dict[str, Any]] = []
        if level >= 0:
            items.append(
                {
                    "source": "skill_distribution",
                    "kind": "skill_descriptor",
                    "content": json.dumps(descriptor, ensure_ascii=False, sort_keys=True),
                    "importance": 1.0,
                    "source_quality": 1.0,
                }
            )
        if level >= 1 and data.get("instructions"):
            items.append(
                {
                    "source": "skill_distribution",
                    "kind": "skill_instructions",
                    "content": str(data["instructions"]),
                    "importance": 0.9,
                    "source_quality": 1.0,
                }
            )
        for resource in data.get("resources", []) if level >= 2 else []:
            items.append(
                {
                    "source": "skill_distribution",
                    "kind": "skill_resource_ref",
                    "content": json.dumps(resource, ensure_ascii=False, sort_keys=True),
                    "importance": 0.4 if resource.get("level", 2) == 2 else 0.2,
                    "source_quality": 1.0,
                }
            )
        ranked = self.score_sources(items)
        selected = select_context_window(
            ranked_items=ranked["ranked_items"], token_budget=token_budget
        )
        return {
            "items": selected["selected_items"],
            "level": level,
            "used_tokens": selected["used_tokens"],
            "token_budget": token_budget,
            "skill": descriptor,
            "authority": 0,
        }

    # Explicit aliases keep the adapter vocabulary discoverable while
    # retaining one implementation and one authority.
    retrieve_skill_context = progressive_disclosure
    disclose_skill = progressive_disclosure

    def score_sources(
        self,
        items: list[dict[str, Any]],
        *,
        query: str | Mapping[str, Any] | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Score source metadata through the existing deterministic ranker."""
        return rank_context_items(items=items, query=query, weights=weights)


def messages_from_dicts(data: list[dict[str, Any]]) -> list[ContextMessage]:
    """从 dict 列表构造消息。"""
    return [
        ContextMessage(
            role=m.get("role", ROLE_USER),
            content=m.get("content", ""),
            priority=m.get("priority", 1),
            ts=m.get("ts", 0.0),
        )
        for m in data
    ]


def rank_context_items(
    *,
    items: list[dict[str, Any]],
    query: str | Mapping[str, Any] | None = None,
    context_goal: str | Mapping[str, Any] | None = None,
    weights: dict[str, float] | None = None,
    token_budget: int | None = None,
) -> dict[str, Any]:
    """Rank caller-supplied context items without persistence or business state.

    This is deliberately lexical and deterministic.  ``count_tokens`` and
    ``truncate_for_context`` remain the atomic token/size authorities; this
    skill only combines their results with item metadata.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list of dictionaries")
    if any(not isinstance(item, dict) for item in items):
        raise TypeError("each context item must be a dictionary")
    weights = weights or {}
    goal = query if query is not None else context_goal
    goal_text = str(goal).lower() if goal is not None else ""
    budget = token_budget if token_budget is not None else 0
    scored: list[tuple[float, int, dict[str, Any], dict[str, float]]] = []
    for index, item in enumerate(items):
        content = str(item.get("content", item.get("text", "")))
        compact_content = truncate_for_context(content, max_bytes=50_000)
        tokens = count_tokens(compact_content)
        words = set(goal_text.split())
        content_words = set(compact_content.lower().split())
        relevance = len(words & content_words) / max(1, len(words)) if words else 0.0
        recency = float(item.get("recency", item.get("timestamp", 0.0)) or 0.0)
        importance = float(item.get("importance", item.get("priority", 0.0)) or 0.0)
        quality = float(item.get("source_quality", item.get("quality", 0.0)) or 0.0)
        efficiency = (importance + quality + 1.0) / max(1, tokens)
        signals = {
            "relevance": relevance,
            "recency": recency,
            "importance": importance,
            "source_quality": quality,
            "token_value_efficiency": efficiency,
        }
        score = sum(
            signals[name] * float(weight) for name, weight in weights.items() if name in signals
        )
        if not weights:
            score = relevance + importance + quality + efficiency
        scored.append((score, index, item, signals))
    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return {
        "ranked_items": [entry[2] for entry in scored],
        "scores": [entry[0] for entry in scored],
        "metadata": {
            "count": len(scored),
            "token_budget": budget,
            "composed_primitives": ["count_tokens", "truncate_for_context"],
        },
    }


def select_context_window(
    *,
    ranked_items: list[dict[str, Any]],
    token_budget: int,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a deterministic, budget-bounded window from ranked items."""
    if token_budget <= 0:
        raise ValueError("token_budget must be > 0")
    if any(not isinstance(item, dict) for item in ranked_items):
        raise TypeError("each ranked item must be a dictionary")
    constraints = constraints or {}
    excluded: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    used = 0
    for item in ranked_items:
        if item.get("excluded") or item.get("include") is False:
            excluded.append(item)
            continue
        tokens = count_tokens(truncate_for_context(str(item.get("content", item.get("text", "")))))
        if constraints.get("max_items") is not None and len(selected) >= int(
            constraints["max_items"]
        ):
            excluded.append(item)
        elif used + tokens <= token_budget:
            selected.append(item)
            used += tokens
        else:
            excluded.append(item)
    return {
        "selected_items": selected,
        "excluded_items": excluded,
        "used_tokens": used,
        "budget_tokens": token_budget,
        "truncated": bool(excluded),
        "metadata": {"composed_primitives": ["count_tokens", "truncate_for_context"]},
    }


def compact_context(
    *,
    items: list[dict[str, Any]],
    token_budget: int,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stateless deterministic context transformation.

    This does not replace ``omodul.context_compactor``: it has no session,
    trail, fingerprint transaction, output directory, or LLM summarisation.
    """
    ranked = rank_context_items(items=items, token_budget=token_budget)
    return select_context_window(
        ranked_items=ranked["ranked_items"],
        token_budget=token_budget,
        constraints=constraints,
    ) | {"ranking": ranked}


def _as_serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _as_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_as_serializable(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _as_serializable(to_dict())
    if hasattr(value, "__dict__"):
        return _as_serializable(vars(value))
    return str(value)


__all__ = [
    "CodeKnowledgeGraphPort",
    "ContextBudget",
    "ContextEngine",
    "ContextMessage",
    "ObservationJournalPort",
    "ROLE_ASSISTANT",
    "ROLE_SYSTEM",
    "ROLE_TOOL",
    "ROLE_USER",
    "TrimResult",
    "compact_context",
    "messages_from_dicts",
    "rank_context_items",
    "select_context_window",
    "SkillDisclosurePort",
]
