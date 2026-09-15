"""oskill.zero_trust_vault — zero-trust secrets vault skill with HITL approval.

3O layer: oskill (composite skill over oprim.fernet_vault + obase.secrets_store).
The LLM never touches real secret strings: it passes only intent + a vault_id
reference. The skill suspends the calling coroutine (asyncio.Event), publishes
a HITL_REQUIRED event to obase.event_bus (the host bridges it to SSE), and
only after human approval decrypts and injects the secret into the physical
callback via an implicit ``_injected_secret`` parameter.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable

from obase.event_bus import EventBus, default_event_bus
from obase.secrets_store import SecretsStore
from obase.tool_governance import redact_payload

_log = logging.getLogger(__name__)

DEFAULT_APPROVAL_TIMEOUT = 300.0


class VaultSkillError(RuntimeError):
    """Raised on vault misuse (unknown credential, missing callback)."""


class ZeroTrustVault:
    """HITL-gated secrets vault: approval suspend -> decrypt -> inject."""

    def __init__(
        self,
        store: SecretsStore | None = None,
        event_bus: EventBus | None = None,
        approval_timeout: float = DEFAULT_APPROVAL_TIMEOUT,
    ):
        self.store = store or SecretsStore()
        self.event_bus = event_bus or default_event_bus
        self.approval_timeout = approval_timeout

        # Async suspended approvals: task_id -> asyncio.Event
        self.pending_approvals: dict[str, asyncio.Event] = {}
        self.approval_results: dict[str, bool] = {}

    # ── 密钥管理(仅后端/运维调用, 绝不暴露给大模型) ──────────────────
    def set_secret(self, vault_id: str, secret: str) -> str:
        return self.store.set_secret(vault_id, secret)

    def has_secret(self, vault_id: str) -> bool:
        return self.store.has_secret(vault_id)

    def list_secret_ids(self) -> list[str]:
        return self.store.list_secret_ids()

    def delete_secret(self, vault_id: str) -> str:
        return self.store.delete_secret(vault_id)

    # ── HITL 审批执行 (核心) ─────────────────────────────────────────
    async def execute_secure_tool(
        self,
        tool_name: str,
        intent_args: dict,
        required_vault_id: str,
        physical_tool_callback: Callable[..., Awaitable[str]],
        *,
        timeout: float | None = None,
    ) -> str:
        """Validate credential -> suspend for human approval -> inject secret."""
        if not self.store.has_secret(required_vault_id):
            return f"❌ 拒绝访问: 金库中不存在凭据 ID '{required_vault_id}'"

        task_id = f"secure_exec_{uuid.uuid4().hex[:12]}"
        approval_event = asyncio.Event()
        self.pending_approvals[task_id] = approval_event

        # 1. 事件总线播报: 拦截! 要求人类介入 (HITL) — 宿主桥接 SSE
        _log.warning("vault: intercepting %s, waiting for human approval (%s)", tool_name, task_id)
        self.event_bus.publish(
            "vault_hitl",
            {
                "level": "HITL_REQUIRED",
                "title": "⚠️ 请求动用生产密钥",
                "content": (
                    f"Agent 请求提取 '{required_vault_id}' 以执行操作: {tool_name}。\n"
                    f"参数: {json.dumps(redact_payload(intent_args), ensure_ascii=False)[:500]}"
                ),
                "task_id": task_id,
                "action": tool_name,
                "vault_id": required_vault_id,
            },
        )

        # 2. 协程异步挂起(绝不阻塞其他并发任务), 死等人类的点击操作
        try:
            await asyncio.wait_for(approval_event.wait(), timeout=timeout or self.approval_timeout)
        except TimeoutError:
            self.pending_approvals.pop(task_id, None)
            self.approval_results.pop(task_id, None)
            _log.info("vault: task %s approval timed out — auto rejected", task_id)
            self._publish_resolved(task_id, approved=False, reason="timeout")
            limit = timeout or self.approval_timeout
            return f"❌ 执行失败: 审批超时(超过 {limit:.0f}s 无人响应), 已自动拒绝。"

        # 3. 检查人类审批结果
        is_approved = self.approval_results.pop(task_id, False)
        self.pending_approvals.pop(task_id, None)
        if not is_approved:
            _log.info("vault: task %s rejected by human", task_id)
            self._publish_resolved(task_id, approved=False, reason="rejected")
            return "❌ 执行失败: 已由系统管理员 (Human) 拒绝授权。"

        # 4. 人类授权通过! 解密真实 Key, 直连物理引擎, 大模型全程瞎眼
        real_secret = self.store.get_secret(required_vault_id)
        _log.info("vault: approved — injecting %s into physical layer", required_vault_id)
        try:
            result = await physical_tool_callback(**intent_args, _injected_secret=real_secret)
        except Exception as exc:  # noqa: BLE001 — never expose physical error text
            self._publish_resolved(task_id, approved=True, reason="physical_error")
            return f"❌ 底层执行崩溃: {type(exc).__name__}"
        self._publish_resolved(task_id, approved=True, reason="approved")
        return f"✅ 授权执行完毕。反馈: {result}"

    # ── 人类审批入口(前端悬浮窗按钮 → 宿主路由) ──────────────────────
    def _publish_resolved(self, task_id: str, approved: bool, reason: str) -> None:
        """广播审批终止事件 — 宿主据此关闭对应 HITL 悬浮窗(审批/拒绝/超时均通知)。"""
        self.event_bus.publish(
            "vault_resolved",
            {"task_id": task_id, "approved": approved, "reason": reason},
        )

    def resolve_approval(self, task_id: str, approved: bool) -> bool:
        """Record the human verdict and wake the suspended coroutine."""
        event = self.pending_approvals.get(task_id)
        if event is None:
            return False
        self.approval_results[task_id] = approved
        event.set()
        _log.info(
            "vault: human approval delivered: %s -> %s",
            task_id,
            "APPROVED" if approved else "REJECTED",
        )
        return True

    def get_pending(self) -> list[dict]:
        return [{"task_id": tid} for tid in self.pending_approvals]
