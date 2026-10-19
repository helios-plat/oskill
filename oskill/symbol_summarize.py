"""3O 范式内化 — Graft 符号摘要技能 (oskill, LLM 经协议注入).

无状态: 不读写任何文件, 摘要结果由上层落盘。
"""

from __future__ import annotations

from oskill.protocols import LLMCaller


async def summarize_symbol(symbol_name: str, *, code: str, llm: LLMCaller) -> str:
    """生成代码符号的一句话摘要 (Graft 节点 summary 字段)。

    Args:
        symbol_name: 符号名 (函数/类/文件)。
        code: 符号的 Crux 代码段。
        llm: LLM 调用协议 (依赖注入)。
    """
    prompt = (
        f"Summarize the following code symbol in one sentence (Chinese or English, "
        f"<30 words). Return ONLY the summary, no markdown.\n\n"
        f"Symbol: {symbol_name}\n\n"
        f"```\n{code[:4000]}\n```"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return str(response.get("content", "")).strip()
