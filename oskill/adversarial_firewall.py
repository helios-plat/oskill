"""oskill.adversarial_firewall — external-data quarantine skill.

3O layer: oskill (composite skill over oprim.injection_scan).
Static heuristic signature scan + quarantine cage wrapping for any external
text (GitHub webhooks, X/Twitter, scraped pages) BEFORE it reaches the LLM,
preventing prompt-injection from escalating instruction privilege.
"""

from __future__ import annotations

import logging
from typing import Any

from oprim._injection_scan import (
    INJECTION_SIGNATURES,
    quarantine_wrap,
    scan_injection,
)

_log = logging.getLogger(__name__)

# 外部内容长度上限(超出截断 — 防巨型 payload 拖垮上下文)
MAX_CONTENT_CHARS = 20000


class AdversarialFirewall:
    """Quarantine + signature-scan firewall for untrusted external text."""

    def __init__(
        self, signatures: tuple[str, ...] | None = None, max_chars: int = MAX_CONTENT_CHARS
    ):
        self.signatures = tuple(signatures or INJECTION_SIGNATURES)
        self.max_chars = max_chars

    def sanitize(self, raw_content: str, source: str = "external_web") -> dict[str, Any]:
        """Filter + format external text.

        Returns {safe, reason, sanitized_content}:
        - unsafe: injection signature matched -> blocked with alert stub.
        - safe:   content quarantined inside <untrusted_external_data> cage.
        """
        raw = str(raw_content or "")
        if len(raw) > self.max_chars:
            raw = raw[: self.max_chars] + "\n... [truncated by firewall]"

        # 1. 静态特征码检测
        matched = scan_injection(raw)
        if matched is not None:
            _log.warning("firewall: injection signature blocked: %r", matched)
            return {
                "safe": False,
                "reason": f"Detected prompt injection signature: '{matched}'",
                "sanitized_content": (
                    "[SECURITY ALERT: External source attempted prompt injection and was blocked.]"
                ),
            }

        # 2. 隔离舱包裹: 强行压制外部数据的指令特权
        return {
            "safe": True,
            "reason": "Passed adversarial firewall checks.",
            "sanitized_content": quarantine_wrap(raw, origin=source),
        }
