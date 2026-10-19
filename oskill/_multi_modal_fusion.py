"""oskill.multi_modal_fusion — 图像、文档与文本图文融合推演技能.

组合 oprim.image_analyze（多模态结构化分析）+ oprim.llm_chat_call（推演），
把图像分析结果与文档/文本上下文拼入统一推理 prompt。stateless。

Example:
    >>> r = await multi_modal_fusion(
    ...     {"image": ["chart.png"], "text": "这是季度报表"},
    ...     prompt="总结关键趋势", provider="qwen_vl", caller=my_caller,
    ... )
    >>> "conclusion" in r
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oprim import image_analyze, llm_chat_call

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class FusionCaller(Protocol):
    """LLM 推演调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def multi_modal_fusion(
    inputs: dict[str, Any],
    *,
    prompt: str,
    caller: FusionCaller,
    provider: str = "qwen_vl",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """图文融合推演。

    Args:
        inputs: 输入素材，支持 {"image": [paths], "text": str|list, "doc": [paths]}。
        prompt: 推演指令。
        caller: LLM 调用器（注入）。
        provider: VLM provider 名（用于 image_analyze）。
        max_tokens: 推演输出上限。

    Returns:
        {"conclusion": str, "evidence": [dict], "inputs_count": int}

    Raises:
        OskillError: prompt 为空 / 无任何素材。
        LLMOskillError: 融合推演失败。
    """
    if not prompt or not prompt.strip():
        raise OskillError("multi_modal_fusion: prompt must not be empty")
    if not inputs:
        raise OskillError("multi_modal_fusion: inputs must not be empty")


    evidence: list[dict[str, Any]] = []

    images = inputs.get("image") or []
    if isinstance(images, str):
        images = [images]
    for img in images:
        try:
            r = await image_analyze(str(img), prompt="结构化描述这张图的内容", provider=provider)
            evidence.append({"type": "image", "source": str(img), "text": r["text"]})
        except Exception as exc:  # noqa: BLE001 - 单图失败不致命
            evidence.append({"type": "image", "source": str(img), "error": str(exc)})

    text_parts = inputs.get("text") or []
    if isinstance(text_parts, str):
        text_parts = [text_parts]
    for i, t in enumerate(text_parts):
        evidence.append({"type": "text", "source": f"text[{i}]", "text": str(t)[:4000]})

    docs = inputs.get("doc") or []
    if isinstance(docs, str):
        docs = [docs]
    for doc in docs:
        try:
            with open(doc, encoding="utf-8", errors="replace") as fh:
                content = fh.read(4000)
            evidence.append({"type": "doc", "source": str(doc), "text": content})
        except OSError as exc:  # noqa: BLE001
            evidence.append({"type": "doc", "source": str(doc), "error": str(exc)})

    if not evidence:
        raise OskillError("multi_modal_fusion: no usable evidence from inputs")

    context = "\n\n".join(
        f"[{e.get('type')}] {e.get('source')}:\n{e.get('text', e.get('error', ''))}"
        for e in evidence
    )
    try:
        resp = await llm_chat_call(
            [
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n素材:\n{context}\n\n基于素材给出结论，并标注依据来源。"
                    ),
                }
            ],
            caller=caller,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        raise LLMOskillError("multi_modal_fusion: fusion call failed", cause=exc) from exc

    return {
        "conclusion": resp["text"],
        "evidence": evidence,
        "inputs_count": len(evidence),
    }
