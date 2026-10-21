"""oskill.marketplace — 内容变现任务市场 (AiToEarn 机制 3O 内化)。

在 social_publish 结算之上补任务市场闭环:
  * **Listing** — 商家发布任务 (需求/预算/结算模式);
  * **Marketplace** — 发布/领取/交付/结算 状态机;
  * 创作者接单 → 内容发布 (publish_fn 注入) → 交付 → settle。
零 veya 反向依赖: 发布函数注入; 纯状态机。
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

STATUS_OPEN = "open"
STATUS_CLAIMED = "claimed"
STATUS_DELIVERED = "delivered"
STATUS_SETTLED = "settled"
STATUSES = (STATUS_OPEN, STATUS_CLAIMED, STATUS_DELIVERED, STATUS_SETTLED)


@dataclass
class Listing:
    """一个变现任务 (商家发布)。"""

    id: str
    merchant: str
    brief: str
    budget: float = 0.0
    settlement: str = "fixed"
    status: str = STATUS_OPEN
    creator: str = ""
    platform: str = ""
    content_id: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "merchant": self.merchant,
            "brief": self.brief,
            "budget": self.budget,
            "settlement": self.settlement,
            "status": self.status,
            "creator": self.creator,
            "platform": self.platform,
            "content_id": self.content_id,
        }


PublishFn = Callable[[Listing, dict[str, Any]], str]
"""发布函数: (listing, 内容) → content_id (注入平台发布)。"""


class Marketplace:
    """任务市场状态机: 发布 → 领取 → 交付 → 结算。"""

    def __init__(self) -> None:
        self.listings: dict[str, Listing] = {}

    def post(
        self, merchant: str, brief: str, *, budget: float = 0.0, settlement: str = "fixed"
    ) -> Listing:
        """商家发布任务。"""
        listing = Listing(
            id=f"task_{uuid.uuid4().hex[:8]}",
            merchant=merchant,
            brief=brief,
            budget=budget,
            settlement=settlement,
        )
        self.listings[listing.id] = listing
        return listing

    def claim(self, listing_id: str, creator: str) -> Listing:
        """创作者领取任务。"""
        listing = self._get(listing_id)
        if listing.status != STATUS_OPEN:
            raise ValueError(f"task not open: {listing.status}")
        listing.status = STATUS_CLAIMED
        listing.creator = creator
        return listing

    def deliver(
        self,
        listing_id: str,
        creator: str,
        *,
        platform: str,
        content: dict[str, Any],
        publish_fn: PublishFn,
    ) -> Listing:
        """创作并交付 (发布内容 → 记录 content_id)。"""
        listing = self._get(listing_id)
        if listing.status != STATUS_CLAIMED or listing.creator != creator:
            raise ValueError(f"task not claimed by {creator}")
        listing.content_id = publish_fn(listing, content)
        listing.platform = platform
        listing.status = STATUS_DELIVERED
        return listing

    def settle(
        self, listing_id: str, *, units: int | None = None, revenue: float | None = None
    ) -> float:
        """结算 (复用 social_publish.settle 语义)。"""
        listing = self._get(listing_id)
        if listing.status != STATUS_DELIVERED:
            raise ValueError(f"task not delivered: {listing.status}")
        from oskill.social_publish import SocialTask
        from oskill.social_publish import settle as _settle

        amount = _settle(
            SocialTask(
                listing.id, listing.merchant, price=listing.budget, settlement=listing.settlement
            ),
            units=units,
            revenue=revenue,
        )
        listing.status = STATUS_SETTLED
        return amount

    def _get(self, listing_id: str) -> Listing:
        listing = self.listings.get(listing_id)
        if listing is None:
            raise KeyError(f"unknown listing: {listing_id!r}")
        return listing

    def list_by_status(self, status: str) -> list[Listing]:
        return [listing for listing in self.listings.values() if listing.status == status]

    def summary(self) -> dict[str, int]:
        return {s: len(self.list_by_status(s)) for s in STATUSES}


__all__ = [
    "Listing",
    "Marketplace",
    "STATUS_CLAIMED",
    "STATUS_DELIVERED",
    "STATUS_OPEN",
    "STATUS_SETTLED",
    "STATUSES",
]
