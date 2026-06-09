"""Cognitive modeling skills (BKT + FSRS integration)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from oprim.cognitive import (
    KCState,
    bkt_update,
    bkt_classify_error,
    fsrs_retrievability,
    fsrs_map_rating,
    fsrs_review,
)

def cognitive_update(
    *,
    kc_state: KCState,
    card_dict: dict,
    is_correct: bool,
    used_answer: bool = False,
    struggled: bool = False,
    effortless: bool = False,
    is_interleaved: bool = False,
    now: Optional[datetime] = None,
) -> dict:
    """Forgetting-aware BKT + FSRS 统一认知更新（stateless，不持久化）。

    更新顺序（MUST）：
    1. 用旧 card_dict 算 R（fsrs_retrievability）
    2. forgetting-aware BKT 更新（R 衰减先验，bkt_update）
    3. 答错则 bkt_classify_error
    4. fsrs_map_rating -> fsrs_review（更新卡片）
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. 计算当前可提取性 R
    r = fsrs_retrievability(card_dict=card_dict, now=now)

    # 2. BKT 更新 (forgetting-aware)
    bkt_update(
        state=kc_state,
        is_correct=is_correct,
        retrievability=r
    )

    # 3. 错误分类 (使用更新后的状态)
    error_type = None
    if not is_correct:
        error_type = bkt_classify_error(state=kc_state)

    # 4. FSRS 卡片更新
    rating = fsrs_map_rating(
        is_correct=is_correct,
        used_answer=used_answer,
        struggled=struggled,
        effortless=effortless
    )
    new_card_dict = fsrs_review(card_dict=card_dict, rating=rating, now=now)

    # 5. 计算有效掌握度
    effective_mastery = (kc_state.long_term_mastery or 0.0) * r

    return {
        "kc_state": kc_state,
        "new_card_dict": new_card_dict,
        "error_type": error_type,
        "rating": rating,
        "effective_mastery": effective_mastery,
    }
