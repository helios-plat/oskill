"""oskill.agent_wiring — 多 agent 指令文件集成 (NanoNets/Graft init 机制 3O 内化)。

把一段指令 (如语义图使用说明) 写入各 coding agent 的原生指令文件:

  * AGENTS.md               — Codex / OpenCode 等读 AGENTS 的 CLI;
  * GEMINI.md               — Gemini CLI;
  * .github/copilot-instructions.md — Copilot;
  * .claude/skills/<name>/SKILL.md  — Claude Code (owned file, 不碰 CLAUDE.md);
  * .cursor/rules/<name>.mdc        — Cursor;
  * .windsurf/rules/<name>.md       — Windsurf;
  * .kiro/steering/<name>.md        — Kiro;
  * .adal/skills/<name>/SKILL.md    — AdaL。

共享指令文件 (AGENTS.md/GEMINI.md/copilot) 用 marker-fenced section 写入,
只更新自己的区块, 不碰用户内容; owned file 完全由本模块拥有, 重建可覆盖。
--dry-run 预览; 无 TTY 默认不写。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── agent 定义表 ─────────────────────────────────────────────────────

AGENT_AGENTS = "agents"
AGENT_GEMINI = "gemini"
AGENT_COPILOT = "copilot"
AGENT_CLAUDE = "claude"
AGENT_CURSOR = "cursor"
AGENT_WINDSURF = "windsurf"
AGENT_KIRO = "kiro"
AGENT_ADAL = "adal"

_AGENTS: dict[str, dict[str, Any]] = {
    AGENT_AGENTS: {"file": "AGENTS.md", "owned": False},
    AGENT_GEMINI: {"file": "GEMINI.md", "owned": False},
    AGENT_COPILOT: {"file": ".github/copilot-instructions.md", "owned": False},
    AGENT_CLAUDE: {"file": ".claude/skills/{name}/SKILL.md", "owned": True},
    AGENT_CURSOR: {"file": ".cursor/rules/{name}.mdc", "owned": True},
    AGENT_WINDSURF: {"file": ".windsurf/rules/{name}.md", "owned": True},
    AGENT_KIRO: {"file": ".kiro/steering/{name}.md", "owned": True},
    AGENT_ADAL: {"file": ".adal/skills/{name}/SKILL.md", "owned": True},
}


@dataclass
class WiringResult:
    """指令写入结果。"""

    agent: str
    file: str
    action: str  # written | updated | skipped | unchanged
    detail: str = ""


def list_agents() -> list[str]:
    """已知 agent id。"""
    return sorted(_AGENTS)


def plan_wiring(
    instruction: str,
    *,
    root: str | Path,
    skill_name: str = "veya",
    agents: list[str] | None = None,
) -> list[WiringResult]:
    """预览 (dry-run): 计算每个 agent 将要写的文件与动作, 不写盘。

    Args:
        instruction: 指令内容。
        root: 项目根。
        skill_name: owned file 的名字 (claude/cursor/windsurf/kiro/adal)。
        agents: 要写的 agent 列表; None = 全部已知。

    Returns:
        WiringResult 列表 (action=written/updated/skipped/unchanged)。
    """
    selected = agents or list_agents()
    results: list[WiringResult] = []
    for agent in selected:
        if agent not in _AGENTS:
            results.append(WiringResult(agent, "", "skipped", f"unknown agent: {agent}"))
            continue
        spec = _AGENTS[agent]
        rel_file = spec["file"].format(name=skill_name)
        target = Path(root) / rel_file
        if spec["owned"]:
            action = "written" if not target.exists() else "updated"
            results.append(WiringResult(agent, rel_file, action))
        else:
            # 共享文件: marker-fenced section 更新
            if target.exists():
                text = target.read_text(encoding="utf-8")
                action = "updated" if f"<!-- {skill_name}:" in text else "unchanged"
            else:
                action = "written"
            results.append(WiringResult(agent, rel_file, action))
    return results


def write_agent_instructions(
    instruction: str,
    *,
    root: str | Path,
    skill_name: str = "veya",
    agents: list[str] | None = None,
    dry_run: bool = False,
) -> list[WiringResult]:
    """把指令写入选定的 agent 指令文件。

    Args:
        instruction: 指令内容。
        root: 项目根。
        skill_name: owned file 名字 / marker 名。
        agents: 目标 agent 列表; None = 全部已知。
        dry_run: True 只预览不写盘。

    Returns:
        WiringResult 列表。

    Example:
        >>> r = write_agent_instructions("Use the graph.", root="/tmp/x",
        ...                              agents=["agents"], dry_run=True)
        >>> r[0].agent
        'agents'
    """
    results = plan_wiring(instruction, root=root, skill_name=skill_name, agents=agents)
    if dry_run:
        return results
    base = Path(root)
    for result in results:
        if result.action == "skipped" or not result.file:
            continue
        target = base / result.file
        spec = _AGENTS[result.agent]
        if spec["owned"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_owned(target, instruction)
            result.action = "written"
        else:
            _write_marker_section(target, instruction, skill_name)
            result.action = "written" if result.action == "written" else "updated"
    return results


def _write_owned(target: Path, content: str) -> None:
    """owned file: 完全覆盖 (带文件头)。"""
    target.write_text(content, encoding="utf-8")


def _write_marker_section(target: Path, content: str, skill_name: str) -> None:
    """共享文件: 在 marker 区间内更新, 不碰其余内容。"""
    start_marker = f"<!-- {skill_name}:start -->"
    end_marker = f"<!-- {skill_name}:end -->"
    block = f"{start_marker}\n{content}\n{end_marker}"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(block + "\n", encoding="utf-8")
        return
    text = target.read_text(encoding="utf-8")
    if start_marker in text and end_marker in text:
        # 替换 marker 区间
        start = text.index(start_marker)
        end = text.index(end_marker) + len(end_marker)
        new_text = text[:start] + block + text[end:]
    else:
        new_text = text.rstrip() + "\n\n" + block + "\n"
    target.write_text(new_text, encoding="utf-8")


__all__ = [
    "AGENT_AGENTS",
    "AGENT_CLAUDE",
    "AGENT_COPILOT",
    "AGENT_CURSOR",
    "AGENT_GEMINI",
    "AGENT_KIRO",
    "AGENT_WINDSURF",
    "AGENT_ADAL",
    "WiringResult",
    "list_agents",
    "plan_wiring",
    "write_agent_instructions",
]
