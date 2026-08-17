"""fan_out_and_synthesize — best-of-N / leader-synthesizer 共识编排。"""

from __future__ import annotations

import pytest

from oskill._fan_out_synthesize import fan_out_and_synthesize


async def test_single_skips_consensus():
    async def gen(task, i):
        return f"only-{i}"

    out = await fan_out_and_synthesize("t", generate=gen, n=1)
    assert out["method"] == "single"
    assert out["chosen"] == "only-0"


async def test_majority_vote_default():
    # 3 个候选里 "A" 出现两次 → 多数票
    seq = ["A", "B", "A"]

    async def gen(task, i):
        return seq[i]

    out = await fan_out_and_synthesize("t", generate=gen, n=3)
    assert out["method"] == "majority"
    assert out["chosen"] == "A"


async def test_all_distinct_falls_back_to_first():
    async def gen(task, i):
        return f"cand-{i}"

    out = await fan_out_and_synthesize("t", generate=gen, n=3)
    assert out["method"] == "first"
    assert out["chosen"] == "cand-0"


async def test_synthesize_wins_when_provided():
    async def gen(task, i):
        return f"c{i}"

    async def synth(task, cands):
        return "MERGED(" + "+".join(cands) + ")"

    out = await fan_out_and_synthesize("t", generate=gen, n=3, synthesize=synth)
    assert out["method"] == "synthesize"
    assert out["chosen"].startswith("MERGED(")
    assert len(out["candidates"]) == 3


async def test_judge_picks_index():
    async def gen(task, i):
        return {"score": i}

    def judge(task, cands):
        # pick the highest score
        return max(range(len(cands)), key=lambda k: cands[k]["score"])

    out = await fan_out_and_synthesize("t", generate=gen, n=3, judge=judge)
    assert out["method"] == "judge"
    assert out["chosen"] == {"score": 2}


async def test_tolerates_partial_failures():
    async def gen(task, i):
        if i == 1:
            raise RuntimeError("boom")
        return "ok"

    out = await fan_out_and_synthesize("t", generate=gen, n=3)
    assert out["chosen"] == "ok"
    assert len(out["candidates"]) == 2
    assert any("boom" in e for e in out["errors"])


async def test_all_fail_returns_none():
    async def gen(task, i):
        raise ValueError("nope")

    out = await fan_out_and_synthesize("t", generate=gen, n=2)
    assert out["chosen"] is None
    assert out["method"] == "none"


async def test_concurrency_limit_still_completes():
    async def gen(task, i):
        return i

    out = await fan_out_and_synthesize("t", generate=gen, n=5, concurrency=2)
    assert len(out["candidates"]) == 5
