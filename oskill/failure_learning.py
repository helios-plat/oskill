"""oskill.failure_learning — 从失败中学习 (ai-agent-book 第8章 3O 内化)。

机制: 失败记录 → 模式归纳 → 经验库 → 任务检索注入。闭环:
  * record_failure 记录一次失败 (任务/类型/错误/轨迹/教训);
  * learn_experiences 按失败类型归纳去重, 沉淀为可复用经验 (教训+适用场景);
  * match_experience 按任务检索最相关经验, 供调用方注入提示词/护栏;
  * ExperienceStore 持久化到 JSON (或事件流), 跨会话复用。

零 veya 反向依赖: 纯数据结构 + 文件持久化 + 关键词匹配。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FailureRecord:
    """一次失败记录。

    Attributes:
        task: 任务描述 (检索键)。
        failure_type: 失败类型 (如 timeout / auth / parse / logic)。
        error: 错误信息。
        trace: 执行轨迹/上下文 (可选)。
        lesson: 人工或自动提取的教训 (可选)。
        ts: 时间戳。
    """

    task: str
    failure_type: str
    error: str
    trace: str = ""
    lesson: str = ""
    ts: float = field(default_factory=time.time)


@dataclass
class Experience:
    """沉淀后的经验 (按失败类型归纳)。"""

    failure_type: str
    lessons: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)  # 适用场景关键词
    occurrences: int = 1
    last_ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "failure_type": self.failure_type,
            "lessons": self.lessons,
            "triggers": self.triggers,
            "occurrences": self.occurrences,
            "last_ts": self.last_ts,
        }


class ExperienceStore:
    """经验库: 失败记录 → 归纳经验 → 任务检索 (JSON 持久化)。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.experiences: dict[str, Experience] = {}
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for failure_type, item in data.items():
                self.experiences[failure_type] = Experience(
                    failure_type=failure_type,
                    lessons=list(item.get("lessons", [])),
                    triggers=list(item.get("triggers", [])),
                    occurrences=item.get("occurrences", 1),
                    last_ts=item.get("last_ts", 0),
                )
        except (json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        """持久化到 JSON (无路径时 no-op)。"""
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {k: v.to_dict() for k, v in self.experiences.items()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── 记录 ──────────────────────────────────────────────────────────

    def record(self, failure: FailureRecord) -> Experience:
        """记录一次失败: 按类型聚合, 去重教训, 更新触发词与计数。

        Args:
            failure: 失败记录。

        Returns:
            该类型的最新经验。
        """
        exp = self.experiences.get(failure.failure_type)
        if exp is None:
            exp = Experience(failure_type=failure.failure_type)
            self.experiences[failure.failure_type] = exp
        exp.occurrences += 1
        if failure.lesson and failure.lesson not in exp.lessons:
            exp.lessons.append(failure.lesson)
        for token in _triggers_from_task(failure.task):
            if token not in exp.triggers:
                exp.triggers.append(token)
        exp.last_ts = failure.ts
        self.save()
        return exp

    # ── 归纳 (learn_experiences) ──────────────────────────────────────

    def learn(self, records: list[FailureRecord]) -> dict[str, Experience]:
        """批量记录失败并归纳 (与逐个 record 等价, 便于一次沉淀)。"""
        result: dict[str, Experience] = {}
        for record in records:
            result[record.failure_type] = self.record(record)
        return result

    # ── 检索 ──────────────────────────────────────────────────────────

    def match(self, task: str, *, top_k: int = 2) -> list[Experience]:
        """按任务检索最相关经验 (触发词重叠打分)。

        Args:
            task: 任务描述。
            top_k: 返回数量。

        Returns:
            经验列表 (得分降序)。
        """
        task_tokens = set(_triggers_from_task(task))
        scored: list[tuple[int, Experience]] = []
        for exp in self.experiences.values():
            trigger_tokens = set(
                _triggers_from_task(" ".join(exp.triggers))
            )
            score = len(task_tokens & trigger_tokens)
            if score > 0:
                scored.append((score, exp))
        scored.sort(key=lambda x: (-x[0], x[1].occurrences))
        return [exp for _, exp in scored[:top_k]]

    def summary(self) -> dict[str, Any]:
        """经验库概览。"""
        return {
            "failure_types": sorted(self.experiences),
            "total_lessons": sum(len(e.lessons) for e in self.experiences.values()),
            "total_occurrences": sum(e.occurrences for e in self.experiences.values()),
        }


def _triggers_from_task(task: str) -> list[str]:
    """任务 → 触发词 (英文 token + 中文 bigram)。"""
    tokens: list[str] = re.findall(r"[a-z][a-z0-9-]{1,}", task.lower())
    for seg in re.findall(r"[\u4e00-\u9fff]+", task):
        if len(seg) <= 2:
            tokens.append(seg)
        else:
            tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
    stop = {"the", "and", "for", "with", "this", "that", "into", "from", "获取"}
    return [t for t in tokens if t not in stop][:12]


def format_experiences(experiences: list[Experience]) -> str:
    """把经验格式化为可注入提示词的文本 (LLM 护栏)。

    Args:
        experiences: 检索到的经验。

    Returns:
        提示词文本 (空列表返回空串)。
    """
    if not experiences:
        return ""
    lines = ["已知失败教训 (注入护栏):"]
    for exp in experiences:
        lines.append(f"- [{exp.failure_type}] ({exp.occurrences} 次): " + "; ".join(exp.lessons))
    return "\n".join(lines)
