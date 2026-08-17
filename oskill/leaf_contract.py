"""oskill.leaf_contract — G0 brief + G1 leaf contract checks. Pure."""

from __future__ import annotations

from typing import Any

from obase.intent_brief import IntentBrief

_ALLOWED_ASSIGNEES = frozenset({"hicode", "dsh", "ask"})
_MAX_ASK = 3


def validate_intent_brief(brief: IntentBrief | dict[str, Any]) -> list[str]:
    """plan needs interpretation + acceptance; ask needs 1-3 questions; refuse needs reasons."""
    data = brief if isinstance(brief, IntentBrief) else _coerce_brief(brief)
    errors: list[str] = []
    if data.action == "plan":
        if not data.interpretation.strip():
            errors.append("plan requires interpretation")
        if not any(str(item).strip() for item in data.acceptance_draft):
            errors.append("plan requires non-empty acceptance_draft")
        if data.questions:
            errors.append("plan must not include questions")
    elif data.action == "ask":
        questions = [q.strip() for q in data.questions if str(q).strip()]
        if not questions:
            errors.append("ask requires 1-3 questions")
        elif len(questions) > _MAX_ASK:
            errors.append(f"ask has too many questions: {len(questions)} > {_MAX_ASK}")
    elif data.action == "refuse":
        if not any(str(item).strip() for item in data.reasons):
            errors.append("refuse requires reasons")
    else:
        errors.append(f"unknown action: {data.action}")
    return errors


def validate_leaf_contract(graph_dict: dict[str, Any] | list[Any]) -> list[str]:
    """Every leaf must name files, logic, forbidden, and observable acceptance."""
    tasks = _tasks_of(graph_dict)
    if not isinstance(tasks, list) or not tasks:
        return ["empty task graph"]
    errors: list[str] = []
    for index, item in enumerate(tasks, start=1):
        if not isinstance(item, dict):
            errors.append(f"task[{index}] is not an object")
            continue
        ident = str(item.get("id") or f"T{index}")
        files = _str_list(item.get("files"))
        logic = str(item.get("logic") or "").strip()
        forbidden = _str_list(item.get("forbidden"))
        acceptance = _str_list(item.get("acceptance"))
        assignee = str(item.get("assignee") or "").strip()
        if not files:
            errors.append(f"{ident} missing files")
        if not logic:
            errors.append(f"{ident} missing logic")
        if not forbidden:
            errors.append(f"{ident} missing forbidden")
        if not acceptance:
            errors.append(f"{ident} has empty acceptance")
        if assignee and assignee not in _ALLOWED_ASSIGNEES:
            errors.append(f"{ident} invalid assignee: {assignee}")
    return errors


def _coerce_brief(raw: dict[str, Any]) -> IntentBrief:
    payload = dict(raw or {})
    action = str(payload.get("action") or "ask").strip().lower()
    if action not in {"plan", "ask", "refuse"}:
        action = "ask"
    payload["action"] = action
    return IntentBrief.model_validate(payload)


def _tasks_of(graph_dict: dict[str, Any] | list[Any]) -> Any:
    if isinstance(graph_dict, list):
        return graph_dict
    if isinstance(graph_dict, dict):
        tasks = graph_dict.get("tasks")
        if tasks is None and isinstance(graph_dict.get("graph"), dict):
            return graph_dict["graph"].get("tasks")
        return tasks
    return None


def _str_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []
