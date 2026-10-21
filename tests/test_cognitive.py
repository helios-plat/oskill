"""Tests for oskill.cognitive (delegating dict adapter over cognitive_state).

Two things are pinned here:

1. the dict contract Helios consumes (keys + value types), and
2. the **single-source guard** (SPEC §1.4): ``oskill.cognitive.cognitive_update``
   must produce exactly the same numbers as the canonical
   ``oskill.cognitive_state.cognitive_update`` for the same inputs. If someone
   ever re-implements the algorithm in this module instead of delegating, this
   test starts failing.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import pytest
from oprim.cognitive import KCState, fsrs_new_card

from oskill.cognitive import cognitive_update
from oskill.cognitive_state import CognitiveUpdateInput
from oskill.cognitive_state import cognitive_update as canonical_update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _real_fsrs():
    """Undo the suite-wide ``fsrs`` MagicMock from ``tests/conftest.py``.

    ``conftest.py`` stubs every heavy optional dependency, ``fsrs`` included, so
    the rest of the suite can import oskill without the real scheduler. These
    tests exercise the actual BKT/FSRS update path, so they need the real
    module (it *is* installed in this venv).
    """
    saved = {name: sys.modules[name] for name in list(sys.modules) if name.split(".")[0] == "fsrs"}
    for name in saved:
        del sys.modules[name]
    import importlib

    import oprim.cognitive as _oc
    import oprim.fsrs_engine as _ofe

    import oskill.cognitive_state as _ocs

    importlib.reload(_ofe)
    importlib.reload(_oc)
    importlib.reload(_ocs)
    yield
    for name in [n for n in list(sys.modules) if n.split(".")[0] == "fsrs"]:
        del sys.modules[name]
    sys.modules.update(saved)


def _state(kc_id: str = "kc-1") -> KCState:
    return KCState(kc_id=kc_id)


EXPECTED_KEYS = {"kc_state", "new_card_dict", "error_type", "rating", "effective_mastery"}


def test_returns_the_documented_dict_contract():
    out = cognitive_update(kc_state=_state(), card_dict=fsrs_new_card(), is_correct=True, now=NOW)
    assert set(out) == EXPECTED_KEYS
    assert isinstance(out["kc_state"], KCState)
    assert isinstance(out["new_card_dict"], dict)
    assert isinstance(out["effective_mastery"], float)


def test_correct_answer_has_no_error_type_and_good_rating():
    out = cognitive_update(kc_state=_state(), card_dict=fsrs_new_card(), is_correct=True, now=NOW)
    assert out["error_type"] is None
    assert out["rating"].name == "Good"


def test_wrong_answer_has_an_error_type_and_again_rating():
    out = cognitive_update(kc_state=_state(), card_dict=fsrs_new_card(), is_correct=False, now=NOW)
    assert out["error_type"] is not None
    assert out["rating"].name == "Again"


def test_used_answer_forces_again_rating():
    out = cognitive_update(
        kc_state=_state(),
        card_dict=fsrs_new_card(),
        is_correct=True,
        used_answer=True,
        now=NOW,
    )
    assert out["rating"].name == "Again"


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"is_correct": True}, "Good"),
        ({"is_correct": True, "struggled": True}, "Hard"),
        ({"is_correct": True, "effortless": True}, "Easy"),
    ],
)
def test_rating_mapping_matches_fsrs_semantics(kwargs, expected):
    out = cognitive_update(kc_state=_state(), card_dict=fsrs_new_card(), now=NOW, **kwargs)
    assert out["rating"].name == expected


def test_mutates_kc_state_in_place():
    state = _state()
    out = cognitive_update(kc_state=state, card_dict=fsrs_new_card(), is_correct=True, now=NOW)
    assert out["kc_state"] is state


def test_defaults_now_to_utc_when_omitted():
    out = cognitive_update(kc_state=_state(), card_dict=fsrs_new_card(), is_correct=True)
    assert isinstance(out["new_card_dict"], dict)


# ---------------------------------------------------------------------------
# single-source guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("is_correct", [True, False])
@pytest.mark.parametrize("used_answer", [True, False])
@pytest.mark.parametrize("struggled", [True, False])
def test_delegates_to_canonical_implementation(is_correct, used_answer, struggled):
    """Adapter output must be bit-identical to the canonical element's output."""
    card = fsrs_new_card()

    adapted = cognitive_update(
        kc_state=_state("kc-a"),
        card_dict=dict(card),
        is_correct=is_correct,
        used_answer=used_answer,
        struggled=struggled,
        now=NOW,
    )

    direct = canonical_update(
        input=CognitiveUpdateInput(
            state=_state("kc-a"),
            card_dict=dict(card),
            is_correct=is_correct,
            used_answer=used_answer,
            struggled=struggled,
            now=NOW,
        )
    )

    assert adapted["rating"] == direct.rating_val
    assert adapted["error_type"] == direct.error_type
    assert adapted["effective_mastery"] == pytest.approx(direct.effective_mastery)
    assert adapted["new_card_dict"]["due"] == direct.card_dict["due"]


def test_module_has_no_duplicated_algorithm_body():
    """The adapter must not re-derive R / call oprim atoms itself."""
    import ast
    from pathlib import Path

    import oskill.cognitive as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    forbidden = {
        "fsrs_retrievability",
        "bkt_update",
        "bkt_classify_error",
        "fsrs_review",
        "fsrs_map_rating",
    }
    assert not (called & forbidden), (
        "oskill.cognitive re-implements the update algorithm; it must delegate to "
        f"oskill.cognitive_state instead (found: {called & forbidden})"
    )
