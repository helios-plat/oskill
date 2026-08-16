"""oskill.wechat_review_loop — 公众号写手↔审核↔打回闭环状态机
(主链路 produce_wechat_article 机制 3O 内化; md2wechat 无此能力, 增量)。

机制 (与 veya 主链路一致, 但 LLM 注入分离):
  写手(Writer) → 配图 resolve (可选) → 审核(Reviewer, 只读不改) →
  不通过则定向打回: 整体性问题(主题不符/整体结构) → 全文重写(带约束);
  章节问题 → 只改被点名章节 (patch)。直到通过或达到 max_iterations。
  超限不假装通过: 明确标 best_effort + 遗留问题。

更强 (相对主链路 server/wechat_article_pipeline.py):
  * 状态机是纯逻辑: write/review/revise/resolve_images 全部由调用方注入
    (async 函数), 本模块零 LLM 依赖 — 任何项目可复用同一套闭环语义;
  * 每轮记录 action + changed, 输出完整 action_log, 可审计可测试;
  * full_rewrite vs patch 的判定规则集中可配置 (FULL_REWRITE_CRITERIA)。

零 veya 反向依赖: 纯标准库 + 注入函数。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

# 触发全文重写的审核准则 (集中配置; 或 section 为 None/""/"__all__")
FULL_REWRITE_CRITERIA = ("topic_match",)

# 注入函数类型: 返回 None 表示该步失败 (LLM 输出无法解析等)
WriterFn = Callable[[str, str, str], Awaitable[dict | None]]
ReviewerFn = Callable[
    [dict, list[dict], str, str, int], Awaitable[dict | None]
]
ReviserFn = Callable[[dict, list[dict], str, str], Awaitable[list[dict] | None]]
ImageResolverFn = Callable[[str], Awaitable[dict]]


@dataclass(frozen=True)
class ReviewIssue:
    """一条审核问题 (LLM 审核输出标准化后)."""

    criterion: str
    section: str | None
    detail: str = ""
    fix_instruction: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "section": self.section,
            "detail": self.detail,
            "fix_instruction": self.fix_instruction,
        }


@dataclass
class ReviewRound:
    """一轮闭环的记录 (可审计)."""

    round_no: int
    verdict: dict[str, Any]  # 原始审核结果
    issues: list[ReviewIssue]
    action: str  # passed | full_rewrite | patch | patch_failed | capped
    changed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_no": self.round_no,
            "action": self.action,
            "changed": self.changed,
            "issues": [i.to_dict() for i in self.issues],
        }


def parse_verdict(raw: dict | None) -> tuple[bool, list[ReviewIssue]]:
    """把审核输出标准化为 (passed, issues)。None/无 pass 键 → 判不通过。"""
    if not isinstance(raw, dict) or "pass" not in raw:
        return False, [
            ReviewIssue(
                criterion="reviewer_output",
                section=None,
                detail="审核输出无法解析为 JSON 或缺 pass 字段",
                fix_instruction="重新生成审核结果",
            )
        ]
    issues: list[ReviewIssue] = []
    for item in raw.get("issues") or []:
        if isinstance(item, dict):
            issues.append(
                ReviewIssue(
                    criterion=str(item.get("criterion") or "unknown"),
                    section=item.get("section"),
                    detail=str(item.get("detail") or ""),
                    fix_instruction=str(item.get("fix_instruction") or ""),
                )
            )
    return bool(raw.get("pass")), issues


def needs_full_rewrite(issues: list[ReviewIssue]) -> bool:
    """判定是否整体性问题 → 全文重写 (集中规则)."""
    return any(
        i.criterion in FULL_REWRITE_CRITERIA or i.section in (None, "", "__all__")
        for i in issues
    )


class WechatReviewLoop:
    """写手↔审核↔打回闭环状态机 (纯逻辑, LLM 注入分离).

    Args:
        writer: async (topic, requirements, extra_constraints) -> draft dict|None。
            全文重写时 extra_constraints 携带审核指出的必改问题。
        reviewer: async (draft, image_results, topic, requirements,
            miss_streak) -> 审核原始 dict|None (含 pass/issues)。
        reviser: async (draft, issues, topic, requirements) -> patch 列表|None;
            patch 项: {heading, body, image_brief?} (heading=title/closing 特判)。
        resolve_image: 可选, async (brief) -> {status, path?}; 缺省返回
            {"status": "missing"} (外部配图服务不可用时不阻塞闭环)。
        max_iterations: 最大轮次 (1-5)。
    """

    def __init__(
        self,
        *,
        writer: WriterFn,
        reviewer: ReviewerFn,
        reviser: ReviserFn,
        resolve_image: ImageResolverFn | None = None,
        max_iterations: int = 3,
    ) -> None:
        self.writer = writer
        self.reviewer = reviewer
        self.reviser = reviser
        self.resolve_image = resolve_image
        self.max_iterations = max(1, min(int(max_iterations), 5))

    async def _resolve_images(self, draft: dict) -> list[dict]:
        if self.resolve_image is None:
            return [
                {"status": "missing", "reason": "resolve_image 未注入"}
                for _ in draft.get("sections") or []
            ]
        return [
            await self.resolve_image(str(s.get("image_brief", "")))
            for s in draft.get("sections") or []
        ]

    async def run(self, topic: str, requirements: str) -> dict[str, Any]:
        """执行闭环。

        Args:
            topic: 文章主题。
            requirements: 写作要求。

        Returns:
            {draft, verdict, passed, iterations, best_effort, image_results,
             action_log, issues} — passed=False 时 best_effort=True,
            issues 为遗留问题 (不假装通过)。
        """
        draft = await self.writer(topic, requirements, "")
        if draft is None:
            return {
                "draft": None,
                "verdict": None,
                "passed": False,
                "iterations": 0,
                "best_effort": True,
                "image_results": [],
                "action_log": [],
                "issues": [
                    ReviewIssue(
                        criterion="writer_output",
                        section=None,
                        detail="写手未能生成合法草稿 (LLM 输出无法解析)",
                        fix_instruction="重试或检查模型配置",
                    )
                ],
            }

        image_miss_streak = 0
        image_results: list[dict] = []
        action_log: list[ReviewRound] = []
        verdict_raw: dict | None = None
        passed = False
        iterations = 0

        for iteration in range(1, self.max_iterations + 1):
            iterations = iteration
            image_results = await self._resolve_images(draft)
            miss = any(r.get("status") != "ok" for r in image_results)
            image_miss_streak = image_miss_streak + 1 if miss else 0

            verdict_raw = await self.reviewer(
                draft, image_results, topic, requirements, image_miss_streak
            )
            passed, issues = parse_verdict(verdict_raw)
            if passed:
                action_log.append(
                    ReviewRound(iteration, verdict_raw or {}, issues, "passed")
                )
                break
            if iteration == self.max_iterations:
                action_log.append(
                    ReviewRound(iteration, verdict_raw or {}, issues, "capped")
                )
                break

            if needs_full_rewrite(issues):
                constraints = "\n".join(
                    f"- {i.detail} → {i.fix_instruction}" for i in issues
                )
                new_draft = await self.writer(topic, requirements, constraints)
                changed = new_draft is not None
                if new_draft:
                    draft = new_draft
                action_log.append(
                    ReviewRound(iteration, verdict_raw or {}, issues, "full_rewrite", changed)
                )
                continue

            patches = await self.reviser(draft, [i.to_dict() for i in issues], topic, requirements)
            if patches:
                draft = merge_revision(draft, patches)
                action_log.append(
                    ReviewRound(iteration, verdict_raw or {}, issues, "patch", True)
                )
            else:
                # 解析失败 → 原稿不变, 下一轮大概率仍不通过, 靠 max_iterations 兜底
                action_log.append(
                    ReviewRound(iteration, verdict_raw or {}, issues, "patch_failed", False)
                )

        return {
            "draft": draft,
            "verdict": verdict_raw,
            "passed": passed,
            "iterations": iterations,
            "best_effort": not passed,
            "image_results": image_results,
            "action_log": [r.to_dict() for r in action_log],
            "issues": parse_verdict(verdict_raw)[1],
        }


def merge_revision(draft: dict, patches: list[dict]) -> dict:
    """按 heading 定向合并补丁, 未涉及的章节原样保留。深拷贝, 不污染原稿。

    patch 项约定: {heading: "与原标题完全一致 | title | closing",
    body: 新文本, image_brief?: 可选换配图方向}。

    Example:
        >>> d = {"title": "T", "sections": [{"heading": "A", "body": "1",
        ...                                   "image_brief": "i"}], "closing": "C"}
        >>> m = merge_revision(d, [{"heading": "A", "body": "2"}])
        >>> m["sections"][0]["body"] == "2" and m["closing"] == "C"
        True
    """
    import copy

    merged = copy.deepcopy(draft)
    by_heading = {s.get("heading"): s for s in merged.get("sections", [])}
    for patch in patches:
        heading = patch.get("heading")
        body = patch.get("body", "")
        if heading == "title":
            merged["title"] = body
        elif heading == "closing":
            merged["closing"] = body
        elif heading in by_heading:
            by_heading[heading]["body"] = body
            if patch.get("image_brief"):
                by_heading[heading]["image_brief"] = patch["image_brief"]
    return merged


__all__ = [
    "FULL_REWRITE_CRITERIA",
    "ImageResolverFn",
    "ReviewIssue",
    "ReviewRound",
    "ReviewerFn",
    "ReviserFn",
    "WechatReviewLoop",
    "WriterFn",
    "merge_revision",
    "needs_full_rewrite",
    "parse_verdict",
]
