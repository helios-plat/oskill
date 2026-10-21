"""Cognitive modelling skill — dict-returning adapter over the canonical skill.

3O layer: oskill (algorithm composed from ≥2 oprim).

Why this module exists
----------------------
:mod:`oskill.cognitive_state` is the canonical forgetting-aware BKT + FSRS
update algorithm (``cognitive_update``, Pydantic in / Pydantic out). The Helios
consumer line carried a second, hand-copied implementation of the *same* update
order that returned a plain ``dict`` and took ``kc_state`` as a keyword.

Two implementations of one algorithm is exactly the drift SPEC §1.4 forbids
("写新元素前先查同源; 重复必须收敛单源 — 留一份为 canonical, 另一份改为
re-export/委托别名"). So this module is **a delegating adapter, not a second
implementation**: it builds the canonical input model, calls
``cognitive_state.cognitive_update``, and reshapes the result into the dict
contract Helios already consumes.

The composition (and therefore the update order) lives in one place only —
``oskill.cognitive_state``:

1. ``oprim.fsrs_retrievability`` — retrievability ``R`` of the current card
2. ``oprim.bkt_update``          — forgetting-aware mastery update
3. ``oprim.bkt_classify_error``  — careless-vs-unknown split on a wrong answer
4. ``oprim.fsrs_map_rating`` + ``oprim.fsrs_review`` — card update

Stateless, no persistence: the caller owns the store.
"""

from __future__ import annotations

from datetime import UTC, datetime

from oprim.cognitive import KCState

from oskill.cognitive_state import CognitiveUpdateInput
from oskill.cognitive_state import cognitive_update as _cognitive_update

__all__ = ["cognitive_update"]

__oprim_layer__ = "element"


def cognitive_update(
    *,
    kc_state: KCState,
    card_dict: dict,
    is_correct: bool,
    used_answer: bool = False,
    struggled: bool = False,
    effortless: bool = False,
    is_interleaved: bool = False,
    now: datetime | None = None,
) -> dict:
    """Forgetting-aware BKT + FSRS update, returned as a plain dict.

    Delegates to :func:`oskill.cognitive_state.cognitive_update` (the single
    implementation); this wrapper only adapts the calling convention and the
    result shape. Mutates ``kc_state`` in place, matching the canonical
    element's contract.

    Parameters
    ----------
    kc_state : KCState
        Knowledge-component state to update in place.
    card_dict : dict
        FSRS card state *before* this review (used to derive ``R``).
    is_correct : bool
        Whether the answer was correct.
    used_answer, struggled, effortless : bool
        Response metadata that maps onto the FSRS rating.
    is_interleaved : bool
        Whether the item was interleaved with other KCs. Recorded for the
        caller; the canonical algorithm does not branch on it yet.
    now : datetime, optional
        Review timestamp (UTC default). Injected so tests are deterministic.

    Returns
    -------
    dict
        ``{"kc_state", "new_card_dict", "error_type", "rating",
        "effective_mastery"}`` — ``rating`` is the FSRS ``Rating`` enum member
        (``.name`` / ``.value`` usable, as the Helios consumer expects),
        ``error_type`` is ``None`` on a correct answer.

    Examples
    --------
    >>> from oprim.cognitive import KCState, fsrs_new_card
    >>> state = KCState(kc_id="kc-1")
    >>> out = cognitive_update(
    ...     kc_state=state, card_dict=fsrs_new_card(), is_correct=True
    ... )
    >>> out["rating"].name
    'Good'
    """
    if now is None:
        now = datetime.now(UTC)

    result = _cognitive_update(
        input=CognitiveUpdateInput(
            state=kc_state,
            card_dict=card_dict,
            is_correct=is_correct,
            used_answer=used_answer,
            struggled=struggled,
            effortless=effortless,
            is_interleaved=is_interleaved,
            now=now,
        )
    )

    # Imported lazily so the enum is resolved against the *live* ``fsrs`` module.
    # The suite-wide conftest stubs ``fsrs``; a module-level import would bind
    # the stub instead of the real Rating enum.
    from oprim.fsrs_engine import Rating

    return {
        "kc_state": result.state,
        "new_card_dict": result.card_dict,
        "error_type": result.error_type,
        # The canonical model stores the rating as its string name plus the
        # integer value; rebuild the enum member so callers keep `.name`.
        "rating": Rating(result.rating_val),
        "effective_mastery": result.effective_mastery,
    }
