"""K-G2: two_step_ingest — two-pass LLM knowledge extraction.

Step 1: LLM analysis (entities, concepts, conflict candidates, structure).
Step 2: LLM KU generation using Step 1 results.

Mandate: Step 2 does NOT confirm conflicts — only outputs candidates for
conflict_resolution (K-G1) to adjudicate.
"""
from __future__ import annotations

import json
import re

from oprim._aii_graph_types import TwoStepIngestResult

_STEP1_SYSTEM = "You are a knowledge extraction specialist. Analyze the source text carefully. Output valid JSON only."
_STEP2_SYSTEM = "You are a knowledge unit generator. Generate structured KU candidates from analysis. Output valid JSON only."

_STEP1_TMPL = """\
Analyze the following text for knowledge extraction.

Text:
{source_text}

Existing KU summaries (for context):
{existing_summaries}

Output JSON with:
{{
  "entities": ["list of key entities"],
  "concepts": ["list of core concepts"],
  "conflict_candidates": ["descriptions of potential conflicts with existing KUs"],
  "structure": "brief description of argument structure"
}}"""

_STEP2_TMPL = """\
Based on the following analysis, generate knowledge unit candidates.

Source text:
{source_text}

Analysis from Step 1:
{analysis}

Output JSON with:
{{
  "ku_candidates": [
    {{
      "title": "KU title",
      "content": "KU content",
      "type": "theorem|definition|example|claim|observation",
      "confidence": "high|medium|low"
    }}
  ]
}}

Important: Do NOT confirm conflicts here. Only generate KU content.
Conflict candidates will be verified separately."""


async def two_step_ingest(
    *,
    source_text: str,
    existing_ku_summaries: list[str],
    llm,
) -> TwoStepIngestResult:
    """Two-pass LLM knowledge extraction.

    Composition: llm (LLMCaller injected), called twice independently.
    Step 2 prompt includes Step 1 analysis — fully chained.
    Conflicts are candidates only; conflict_resolution must adjudicate.
    """
    # Step 1: Analysis
    existing_block = "\n".join(f"- {s}" for s in existing_ku_summaries) or "(none)"
    step1_prompt = _STEP1_TMPL.format(
        source_text=source_text, existing_summaries=existing_block
    )
    step1_resp = await llm(
        messages=[{"role": "user", "content": step1_prompt}],
        system=_STEP1_SYSTEM,
        max_tokens=1024,
    )
    analysis = _parse_json(step1_resp) or {
        "entities": [], "concepts": [], "conflict_candidates": [], "structure": ""
    }

    # Step 2: KU Generation (includes Step 1 analysis in prompt)
    step2_prompt = _STEP2_TMPL.format(
        source_text=source_text,
        analysis=json.dumps(analysis, ensure_ascii=False, indent=2),
    )
    step2_resp = await llm(
        messages=[{"role": "user", "content": step2_prompt}],
        system=_STEP2_SYSTEM,
        max_tokens=2048,
    )
    step2_data = _parse_json(step2_resp) or {}
    ku_candidates = step2_data.get("ku_candidates", [])

    return TwoStepIngestResult(
        analysis=analysis,
        ku_candidates=ku_candidates,
        conflict_candidates=analysis.get("conflict_candidates", []),
    )


def _parse_json(resp: dict) -> dict | None:
    text = ""
    for block in resp.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text = block["text"].strip()
            break
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        val = json.loads(text)
        return val if isinstance(val, dict) else None
    except json.JSONDecodeError:
        return None
