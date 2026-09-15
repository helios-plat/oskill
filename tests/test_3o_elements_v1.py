from __future__ import annotations

import json

import pytest

from oskill.context_engineering import ContextEngine
from oskill.skill_distribution_provider import (
    LocalSkillDistributionProvider,
    MemorySkillCache,
    SkillDigestMismatch,
    SkillDistributionError,
)


@pytest.mark.asyncio
async def test_skill_provider_progressive_disclosure_digest_and_resource(tmp_path) -> None:
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text("Use the demo skill.", encoding="utf-8")
    (skill / "guide.txt").write_text("guide", encoding="utf-8")
    (skill / "examples").mkdir()
    (skill / "examples" / "large.txt").write_text("example", encoding="utf-8")
    (skill / "manifest.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "name": "Demo",
                "description": "A test skill",
                "dependencies": [],
            }
        ),
        encoding="utf-8",
    )
    provider = LocalSkillDistributionProvider(tmp_path)
    assert (await provider.list())[0].skill_id == "demo"
    level_one = await provider.get("demo", level=1)
    assert level_one.instructions and not level_one.resources
    level_two = await provider.get("demo", level=2)
    assert any(item.path == "guide.txt" for item in level_two.resources)
    assert all(not item.path.startswith("examples/") for item in level_two.resources)
    assert await provider.fetch_resource(level_one, "guide.txt") == b"guide"
    assert await provider.verify_digest(level_two)
    with pytest.raises(SkillDigestMismatch):
        await provider.resolve({"skill_id": "demo", "version": "1.0.0", "digest": "bad"})

    cache = MemorySkillCache()
    await LocalSkillDistributionProvider(tmp_path, cache=cache).get("demo", level=2)
    offline = LocalSkillDistributionProvider(tmp_path / "offline", cache=cache)
    cached = await offline.get("demo", "1.0.0", level=1)
    assert cached.instructions == "Use the demo skill."


@pytest.mark.asyncio
async def test_context_engine_adapters_keep_provenance_and_budget(tmp_path) -> None:
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text("instructions", encoding="utf-8")
    provider = LocalSkillDistributionProvider(tmp_path)
    context = ContextEngine()
    disclosed = await context.progressive_disclosure(
        provider, "demo", level=1, token_budget=100, business_context={"tenant": "a"}
    )
    assert disclosed["level"] == 1
    assert disclosed["used_tokens"] <= 100


class _GraphFacts:
    async def context_slice(self, symbol, **kwargs):
        return {"root": symbol, "symbols": ["root"], "budget": kwargs["token_budget"]}

    async def impact(self, symbol, **kwargs):
        return {"root": symbol, "files": ["src/app.py"], "depth": kwargs["max_depth"]}


class _Observations:
    async def query(self, **kwargs):
        return [
            {
                "id": "observation-1",
                "scope": kwargs["scope"],
                "source": "session",
                "summary": "terminal output",
            }
        ]


@pytest.mark.asyncio
async def test_context_engine_composes_code_and_observation_ports() -> None:
    context = ContextEngine()
    code = await context.retrieve_code_context(_GraphFacts(), "root", token_budget=200, max_depth=3)
    assert code["authority"] == 0
    assert code["impact"]["files"] == ["src/app.py"]
    assert code["used_tokens"] <= 200

    observations = await context.retrieve_observation_context(
        _Observations(), {"scope": "tenant-a"}, token_budget=200
    )
    assert observations["observation_not_evidence"] is True
    assert observations["items"][0]["source"] == "observation_journal"
    assert observations["used_tokens"] <= 200


@pytest.mark.asyncio
async def test_malformed_skill_is_rejected(tmp_path) -> None:
    skill = tmp_path / "broken"
    skill.mkdir()
    (skill / "SKILL.md").write_text("broken", encoding="utf-8")
    (skill / "manifest.json").write_text("[]", encoding="utf-8")
    provider = LocalSkillDistributionProvider(tmp_path)
    with pytest.raises(SkillDistributionError, match="malformed"):
        await provider.get("broken")
