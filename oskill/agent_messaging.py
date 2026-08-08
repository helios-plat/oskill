"""oskill.agent_messaging — A2A 协议 (hello-agents 第10章 3O 内化)。

Agent-to-Agent 通信机制 (A2A 消息格式 + 任务路由 + 结果回传):
  * **AgentMessage** — A2A 消息 (from/to/task/status/payload);
  * **A2AProtocol** — 消息发送/接收/任务分发路由 (按能力匹配);
  * **AgentBus** — 多 agent 总线: 注册 agent (id/能力) → 路由任务 → 回传
    结果; 与 agent_orchestrator/pentest_squad 组合。
零 veya 反向依赖: 消息处理函数注入; 纯消息路由。
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

MSG_STATUS_REQUEST = "request"
MSG_STATUS_WORKING = "working"
MSG_STATUS_SUCCESS = "success"
MSG_STATUS_ERROR = "error"


@dataclass
class AgentMessage:
    """一条 A2A 消息。"""

    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    from_agent: str = ""
    to_agent: str = ""
    task: str = ""
    status: str = MSG_STATUS_REQUEST
    payload: Any = None
    ts: float = field(default_factory=time.time)
    reply_to: str = ""  # 回复的消息 id

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "task": self.task,
            "status": self.status,
            "payload": self.payload,
            "reply_to": self.reply_to,
        }


AgentHandler = Callable[[AgentMessage], Any]
"""agent 消息处理: (消息) → 结果 (注入)。"""


class A2AProtocol:
    """A2A 消息协议: 发送/接收/回复。"""

    def __init__(self) -> None:
        self.messages: dict[str, AgentMessage] = {}

    def send(
        self, from_agent: str, to_agent: str, task: str, *, payload: Any = None
    ) -> AgentMessage:
        """发送请求消息。"""
        message = AgentMessage(from_agent=from_agent, to_agent=to_agent, task=task, payload=payload)
        self.messages[message.message_id] = message
        return message

    def reply(self, original: AgentMessage, *, status: str, payload: Any = None) -> AgentMessage:
        """回复消息 (回传结果/状态)。"""
        reply = AgentMessage(
            from_agent=original.to_agent,
            to_agent=original.from_agent,
            task=original.task,
            status=status,
            payload=payload,
            reply_to=original.message_id,
        )
        self.messages[reply.message_id] = reply
        return reply

    def get(self, message_id: str) -> AgentMessage | None:
        return self.messages.get(message_id)

    def replies_to(self, message_id: str) -> list[AgentMessage]:
        return [m for m in self.messages.values() if m.reply_to == message_id]

    def recent(self, n: int = 10) -> list[AgentMessage]:
        msgs = sorted(self.messages.values(), key=lambda m: m.ts, reverse=True)
        return msgs[:n]


class AgentBus:
    """多 agent 总线: 注册 → 能力路由 → 派发 → 回传。"""

    def __init__(self) -> None:
        self.agents: dict[str, tuple[list[str], AgentHandler]] = {}
        self.protocol = A2AProtocol()

    def register(self, agent_id: str, capabilities: list[str], handler: AgentHandler) -> None:
        """注册 agent (id + 能力 + 处理函数)。"""
        self.agents[agent_id] = (list(capabilities), handler)

    def route(self, task: str, *, require_capability: str | None = None) -> list[str]:
        """按任务路由: 能力匹配的 agent 列表。"""
        candidates = [
            aid
            for aid, (caps, _) in self.agents.items()
            if require_capability is None or require_capability in caps
        ]
        if require_capability is None:
            return candidates
        return candidates

    def dispatch(
        self,
        from_agent: str,
        task: str,
        *,
        to_agent: str | None = None,
        require_capability: str | None = None,
        payload: Any = None,
    ) -> AgentMessage:
        """派发任务给 agent (指定或按能力路由), 同步处理并回传。

        Args:
            from_agent: 发起者。
            task: 任务。
            to_agent: 指定目标; None 按能力路由首个。
            require_capability: 能力路由条件。

        Returns:
            最终回复消息 (success/error)。
        """
        target = to_agent or self._route_first(task, require_capability)
        if target is None or target not in self.agents:
            return AgentMessage(
                from_agent="bus",
                to_agent=from_agent,
                task=task,
                status=MSG_STATUS_ERROR,
                payload="no capable agent",
            )
        request = self.protocol.send(from_agent, target, task, payload=payload)
        _, handler = self.agents[target]
        try:
            result = handler(request)
            return self.protocol.reply(request, status=MSG_STATUS_SUCCESS, payload=result)
        except Exception as exc:  # noqa: BLE001
            return self.protocol.reply(
                request, status=MSG_STATUS_ERROR, payload=f"{exc.__class__.__name__}: {exc}"
            )

    def _route_first(self, task: str, capability: str | None) -> str | None:
        candidates = self.route(task, require_capability=capability)
        return candidates[0] if candidates else None

    def summary(self) -> dict[str, Any]:
        return {
            "agents": {aid: caps for aid, (caps, _) in self.agents.items()},
            "messages": len(self.protocol.messages),
        }


__all__ = [
    "A2AProtocol",
    "AgentBus",
    "AgentMessage",
    "MSG_STATUS_ERROR",
    "MSG_STATUS_REQUEST",
    "MSG_STATUS_SUCCESS",
    "MSG_STATUS_WORKING",
]
