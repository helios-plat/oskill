"""oskill.provider_clients — 真实 LLM provider 客户端 (freellmapi provider 适配 3O 内化)。

真实 HTTP 客户端适配器 (httpx 优先, urllib 保底):
  * **ProviderClient** — provider 端点/密钥/格式 (openai-compatible / anthropic);
  * **chat_completion** — 非流式对话 (含 tools/temperature);
  * **chat_stream** — 流式 (SSE 解析);
  * **PROVIDER_REGISTRY** — 内置常见 provider 端点表 (openai/anthropic/
    deepseek/zhipu/dashscope/moonshot/openrouter/groq/cerebras/mistral...);
  * 与 model_routing 组合: 真实客户端替代 stub。
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

FORMAT_OPENAI = "openai"  # /chat/completions
FORMAT_ANTHROPIC = "anthropic"  # /v1/messages

# 常见 provider 端点 (freellmapi provider 适配器表, 可扩展)
PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    "openai": {"base": "https://api.openai.com/v1", "format": FORMAT_OPENAI},
    "anthropic": {"base": "https://api.anthropic.com/v1", "format": FORMAT_ANTHROPIC},
    "deepseek": {"base": "https://api.deepseek.com/v1", "format": FORMAT_OPENAI},
    "zhipu": {"base": "https://open.bigmodel.cn/api/paas/v4", "format": FORMAT_OPENAI},
    "dashscope": {
        "base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "format": FORMAT_OPENAI,
    },
    "moonshot": {"base": "https://api.moonshot.cn/v1", "format": FORMAT_OPENAI},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "format": FORMAT_OPENAI},
    "groq": {"base": "https://api.groq.com/openai/v1", "format": FORMAT_OPENAI},
    "cerebras": {"base": "https://api.cerebras.ai/v1", "format": FORMAT_OPENAI},
    "mistral": {"base": "https://api.mistral.ai/v1", "format": FORMAT_OPENAI},
    "together": {"base": "https://api.together.xyz/v1", "format": FORMAT_OPENAI},
    "fireworks": {"base": "https://api.fireworks.ai/inference/v1", "format": FORMAT_OPENAI},
    "xai": {"base": "https://api.x.ai/v1", "format": FORMAT_OPENAI},
    "gemini": {
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "format": FORMAT_OPENAI,
    },
}


@dataclass
class ProviderClient:
    """一个 provider 的 HTTP 客户端。"""

    provider: str
    api_key: str
    base_url: str | None = None
    format: str = FORMAT_OPENAI
    timeout: float = 60.0

    def __post_init__(self) -> None:
        if self.base_url is None:
            spec = PROVIDER_REGISTRY.get(self.provider)
            if spec is None:
                raise ValueError(
                    f"unknown provider: {self.provider!r}; known: {sorted(PROVIDER_REGISTRY)}"
                )
            self.base_url = spec["base"]
            self.format = spec["format"]

    # ── 非流式 ──────────────────────────────────────────────────────

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """非流式对话完成 (真实 HTTP 调用)。"""
        if self.format == FORMAT_ANTHROPIC:
            return self._anthropic_completion(model, messages, max_tokens=max_tokens)
        raw = self._openai_completion(
            model,
            messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return json.loads(raw)

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int = 4096,
    ) -> list[dict[str, Any]]:
        """流式对话完成 (收集为事件列表; 真实流由调用方消费)。"""
        if self.format == FORMAT_ANTHROPIC:
            raise NotImplementedError("anthropic 流式由调用方实现")
        response = self._openai_completion(
            model,
            messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        return _parse_sse_events(response)

    # ── OpenAI-compatible ───────────────────────────────────────────

    def _openai_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None,
        temperature: float | None,
        max_tokens: int,
        stream: bool,
    ) -> str:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = tools
        return self._post(
            f"{self.base_url}/chat/completions",
            body,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    def _anthropic_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int,
    ) -> dict[str, Any]:
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": other_msgs,
        }
        if system_msgs:
            body["system"] = "\n".join(str(m.get("content", "")) for m in system_msgs)
        raw = self._post(
            f"{self.base_url}/messages",
            body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        data = json.loads(raw)
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "".join(
                            block.get("text", "")
                            for block in data.get("content", [])
                            if block.get("type") == "text"
                        ),
                    }
                }
            ],
            "usage": data.get("usage", {}),
        }

    def _post(self, url: str, body: dict[str, Any], *, headers: dict[str, str]) -> str:
        """HTTP POST (httpx 优先, urllib 保底)。"""
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        all_headers = {"Content-Type": "application/json", **headers}
        try:
            import httpx  # noqa: PLC0415

            resp = httpx.post(url, content=data, headers=all_headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except ImportError:
            req = urllib.request.Request(url, data=data, headers=all_headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8")


def _parse_sse_events(raw: str) -> list[dict[str, Any]]:
    """解析 SSE 为事件列表 (OpenAI stream 格式)。"""
    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
    return events


def client_for(provider: str, api_key: str, **kwargs: Any) -> ProviderClient:
    """按 provider 构造客户端 (注册表配置)。"""
    return ProviderClient(provider=provider, api_key=api_key, **kwargs)


__all__ = ["FORMAT_ANTHROPIC", "FORMAT_OPENAI", "PROVIDER_REGISTRY", "ProviderClient", "client_for"]
