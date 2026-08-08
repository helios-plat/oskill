"""oskill.shared_language — 共享语言原语 (mattpocock domain-modeling / CONTEXT.md SKILL 3O 内化)。

机制: 项目术语表 (CONTEXT.md glossary) 的幂等收敛 + 难决策 ADR 门控落盘。
术语决议即时落盘; 只有同时满足三门槛 (难逆转 / 无上下文难懂 / 真权衡) 的
决策才写 ADR。术语表与 ADR 都是纯文本文件, 由调用方指定路径。

零 veya 反向依赖: 纯文件操作, 无外部命令。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── 术语表 (CONTEXT.md glossary) ────────────────────────────────────

_GLOSSARY_HEADER = "## Glossary"
_GLOSSARY_HEADER_ALT = "## 术语表"


def read_glossary(path: str | Path) -> dict[str, str]:
    """读取术语表为 {术语: 定义}。

    支持两种条目格式:
      * 定义列表: ``- **term** — definition``
      * 表格:     ``| term | definition |`` (含表头则跳过)

    Args:
        path: CONTEXT.md 或独立术语表文件路径 (不存在返回空 dict)。

    Returns:
        术语 → 定义 映射 (保持文件顺序)。
    """
    glossary: dict[str, str] = {}
    file_path = Path(path)
    if not file_path.exists():
        return glossary
    in_glossary = False
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped in (_GLOSSARY_HEADER, _GLOSSARY_HEADER_ALT):
            in_glossary = True
            continue
        if not in_glossary:
            continue
        if stripped.startswith("#"):
            break
        m = re.match(r"^[-*]\s+\*\*(.+?)\*\*\s*[—-]\s*(.+)$", stripped)
        if m:
            glossary[m.group(1).strip()] = m.group(2).strip()
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() not in ("term", "术语"):
            glossary[cells[0]] = cells[1]
    return glossary


def upsert_term(
    path: str | Path,
    term: str,
    definition: str,
    *,
    glossary_header: str | None = None,
) -> dict[str, Any]:
    """幂等写入/更新一个术语。

    已有术语 → 原位更新定义; 新术语 → 追加到术语表末尾。术语表不存在时
    在文件末尾创建 (含 header)。

    Args:
        path: CONTEXT.md 路径。
        term: 术语名。
        definition: 定义。
        glossary_header: 覆盖默认 "## Glossary" 标题。

    Returns:
        {term, created, glossary_path, total_terms}
    """
    file_path = Path(path)
    header = glossary_header or _GLOSSARY_HEADER
    existing: dict[str, str] = {}
    lines: list[str] = []
    if file_path.exists():
        lines = file_path.read_text(encoding="utf-8").splitlines()
        existing = read_glossary(file_path)

    if term in existing:
        # 原位更新: 找条目行替换
        new_lines: list[str] = []
        replaced = False
        for line in lines:
            stripped = line.strip()
            m = re.match(r"^([-*])\s+\*\*" + re.escape(term) + r"\*\*\s*[—-]\s*.*$", stripped)
            if m:
                new_lines.append(f"- **{term}** — {definition}")
                replaced = True
            else:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2 and cells[0] == term:
                    new_lines.append(f"| {term} | {definition} |")
                    replaced = True
                else:
                    new_lines.append(line)
        lines = new_lines if replaced else lines
        created = False
    else:
        # 追加: 若无术语表 header 则先补
        has_header = any(ln.strip() in (_GLOSSARY_HEADER, _GLOSSARY_HEADER_ALT) for ln in lines)
        if not has_header:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(header)
            lines.append("")
        # 统一用定义列表格式
        lines.append(f"- **{term}** — {definition}")
        created = True

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {
        "term": term,
        "created": created,
        "glossary_path": str(file_path),
        "total_terms": len(read_glossary(file_path)),
    }


# ── ADR 门控与落盘 ──────────────────────────────────────────────────


@dataclass(frozen=True)
class AdrDraft:
    """ADR 草稿 (mattpocock 三门槛全过才写)。

    Attributes:
        title: ADR 标题 (作为文件名与一级标题)。
        status: Accepted / Proposed / Superseded。
        context: 背景 (为什么有这个问题)。
        decision: 决策本身。
        consequences: 后果 (正/负)。
    """

    title: str
    context: str
    decision: str
    consequences: str
    status: str = "Accepted"


def should_write_adr(
    *,
    reversible: bool,
    obvious_without_context: bool,
    real_tradeoff: bool,
) -> bool:
    """ADR 三门槛: 难逆转 / 无上下文难懂 / 真权衡 —— 同时满足才写。

    Args:
        reversible: 是否难以逆转。
        obvious_without_context: 无上下文是否让人困惑。
        real_tradeoff: 是否真实权衡。

    Returns:
        True 当且仅当三个条件同时成立。
    """
    return (not reversible) and obvious_without_context and real_tradeoff


def write_adr(
    adr_dir: str | Path,
    draft: AdrDraft,
    *,
    index: int | None = None,
) -> str:
    """写一个 ADR 文件到 docs/adr/ 风格目录。

    文件名: ``<index>-<kebab-title>.md``; index None 时按目录已有文件数 +1。

    Args:
        adr_dir: ADR 目录 (自动创建)。
        draft: ADR 草稿。
        index: 序号覆盖。

    Returns:
        写入的文件路径。
    """
    directory = Path(adr_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if index is None:
        index = len(list(directory.glob("*.md"))) + 1
    kebab = re.sub(r"[^\w]+", "-", draft.title.lower()).strip("-")
    target = directory / f"{index:04d}-{kebab}.md"
    body = f"""# {index}. {draft.title}

日期: {__import__("datetime").date.today().isoformat()}

## Status

{draft.status}

## Context

{draft.context}

## Decision

{draft.decision}

## Consequences

{draft.consequences}
"""
    target.write_text(body, encoding="utf-8")
    return str(target)
