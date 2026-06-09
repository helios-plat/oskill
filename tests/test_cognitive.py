"""Tests for cognitive modeling oskill."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from oprim.cognitive import KCState, fsrs_new_card
from oskill.cognitive import cognitive_update

def test_cognitive_update_correct():
    """Correct answer updates mastery and FSRS rating."""
    kc = KCState(kc_id="test", p_init=0.2, p_transit=0.2, p_guess=0.1, p_slip=0.1)
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=True)
    
    assert res["kc_state"].current() > 0.2
    assert res["rating"] == "Good"
    assert "new_card_dict" in res
    assert res["error_type"] is None

def test_cognitive_update_careless():
    """Incorrect answer with very high mastery is careless even after BKT update."""
    kc = KCState(kc_id="test", p_mastery=0.99, p_slip=0.1, p_guess=0.1, p_transit=0.2)
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=False)
    
    assert res["error_type"] == "careless"
    assert res["rating"] == "Again"

def test_cognitive_update_dontknow():
    """Incorrect answer with low mastery is dontknow."""
    kc = KCState(kc_id="test", p_mastery=0.1, p_guess=0.1, p_slip=0.1)
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=False)
    
    assert res["error_type"] == "dontknow"

def test_cognitive_update_used_answer():
    """used_answer signals Again rating."""
    kc = KCState(kc_id="test")
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=True, used_answer=True)
    
    assert res["rating"] == "Again"

def test_cognitive_update_effortless():
    """effortless signals Easy rating."""
    kc = KCState(kc_id="test")
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=True, effortless=True)
    
    assert res["rating"] == "Easy"

def test_cognitive_update_effective_mastery():
    """Effective mastery is mastery * retrievability."""
    kc = KCState(kc_id="test", p_mastery=0.8, long_term_mastery=0.8)
    card = fsrs_new_card()
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=True)
    
    # R for new card is 1.0, so effective_mastery should be ~ p_mastery
    assert pytest.approx(res["effective_mastery"], 0.1) == res["kc_state"].long_term_mastery

def test_cognitive_update_sequence():
    """Ensure update sequence: R -> BKT -> classify -> review."""
    kc = KCState(kc_id="test")
    card = fsrs_new_card()
    
    with patch("oskill.cognitive.fsrs_retrievability", return_value=0.9) as mock_r:
        with patch("oskill.cognitive.bkt_update") as mock_bkt:
            with patch("oskill.cognitive.fsrs_review") as mock_review:
                with patch("oskill.cognitive.fsrs_map_rating") as mock_map:
                    cognitive_update(kc_state=kc, card_dict=card, is_correct=True)
                    
                    # Check R is called first
                    mock_r.assert_called_once()
                    # Check BKT uses that R
                    mock_bkt.assert_called_once()
                    assert mock_bkt.call_args[1]["retrievability"] == 0.9
                    # Check review is called
                    mock_review.assert_called_once()

def test_cognitive_update_integration():
    """End-to-end integration without mocks."""
    kc = KCState(kc_id="test")
    card = fsrs_new_card()
    now = datetime(2026, 6, 7, tzinfo=timezone.utc)
    
    res = cognitive_update(kc_state=kc, card_dict=card, is_correct=True, now=now)
    assert res["kc_state"].n_attempts == 1
    assert res["new_card_dict"]["stability"] is not None
