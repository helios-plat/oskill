"""K-ONT-1: ontology_extract — two-pass LLM knowledge ontology extraction.

Two passes (MUST):
  Pass 1 (global map): chunk text → per-chunk concept/topic extraction →
          aggregate into full-book outline (chapters, core_concepts, main_thread,
          stance, doc_type, source_credibility)
  Pass 2 (KU extraction with outline context): per-chunk + outline →
          6-class KU candidates + edge candidates + concept candidates

Six-class priority (hardcoded in prompt):
  why/mechanism         → explanatory
  how/steps             → procedural
  learning/reflection   → metacognitive
  no truth/positional   → positional  (stance_holder REQUIRED)
  essence/principle     → conceptual  (sub_type filled)
  verifiable fact       → factual

Gate (MUST): arguments/cases → demote to 'example' field or 'supported_by' edge;
             never a standalone KU
Active why-extraction: each concept → explanatory KU + explains edge
grade: always hardcoded "unverified" after LLM, regardless of LLM output
relation_type: invalid ones silently discarded (must be in VALID_RELATION_TYPES)
"""
from __future__ import annotations

import json
import re

from oprim._aii_graph_types import (
    OntologyExtractResult,
    VALID_RELATION_TYPES,
    VALID_KNOWLEDGE_TYPES,
)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_PASS1_CHUNK_SYSTEM = (
    "You are a knowledge analyst. Extract structured information from text chunks. "
    "Output valid JSON only."
)

_PASS1_CHUNK_TMPL = """\
Analyze this text chunk and extract structured knowledge metadata.

Text chunk:
{chunk_text}

Output JSON with:
{{
  "concepts": ["list of core concepts mentioned"],
  "topics": ["main topics covered"],
  "chapter": "chapter or section heading if identifiable, else empty string"
}}"""

_PASS1_OUTLINE_SYSTEM = (
    "You are a knowledge architect. Synthesize chunk analyses into a coherent book outline. "
    "Output valid JSON only."
)

_PASS1_OUTLINE_TMPL = """\
Synthesize these chunk analyses into a full-book outline.

doc_type: {doc_type}
source_credibility: {source_credibility}

Chunk analyses:
{chunk_analyses}

Output JSON with:
{{
  "chapters": ["list of chapter/section names inferred"],
  "core_concepts": ["unified list of core concepts"],
  "main_thread": "one-sentence description of the main argument/thread",
  "stance": "author's overall stance or perspective",
  "doc_type": "{doc_type}",
  "source_credibility": "{source_credibility}"
}}"""

_PASS2_SYSTEM = (
    "You are a knowledge unit extractor. Extract structured KUs from text using strict classification rules. "
    "Output valid JSON only."
)

_SIX_CLASS_RULES = """\
Classification priority (apply in order — first match wins):
1. why / mechanism / reason    → knowledge_type = "explanatory"
2. how / steps / procedure     → knowledge_type = "procedural"
3. learning strategy/reflection → knowledge_type = "metacognitive"
4. no truth value / relative position / opinion → knowledge_type = "positional"
   ⚠ MUST set stance_holder (non-empty string, who holds this position)
5. essence / principle / definition → knowledge_type = "conceptual"
   Fill sub_type from: classification|principle|theory|skill|technique|
                        conditional|strategic|task_knowledge|self_knowledge
6. verifiable fact              → knowledge_type = "factual"

GATE (strictly enforced):
- Arguments, examples, supporting evidence → NOT standalone KUs
  → Demote: add as 'example' field on a KU, or create a 'supported_by' edge
- Do NOT create KUs for mere illustrations or anecdotes

ACTIVE WHY-EXTRACTION (required):
- For each key concept found, ask WHY it works / what mechanism underlies it
- If a mechanism exists → create an explanatory KU + an 'explains' edge

grade: always set to "unverified" regardless of evidence strength"""

_PASS2_CHUNK_TMPL = """\
Extract knowledge units from this text chunk.

Full-book outline (context):
{outline}

Text chunk:
{chunk_text}

{six_class_rules}

Output JSON with:
{{
  "ku_candidates": [
    {{
      "id": "temp_<n>",
      "title": "concise KU title",
      "content": "KU content",
      "knowledge_type": "<one of six types>",
      "grade": "unverified",
      "sub_type": "<sub_type or null>",
      "stance_holder": "<required for positional, else null>",
      "example": "<supporting example if demoted, else null>",
      "concepts": ["referenced concepts"]
    }}
  ],
  "edge_candidates": [
    {{"source": "<ku_id>", "target": "<ku_id or concept>", "relation_type": "<controlled type>"}}
  ],
  "concept_candidates": ["new concepts discovered in this chunk"]
}}"""


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

async def ontology_extract(
    *,
    source_text: str,
    chunk_size: int = 2000,
    llm,
    doc_type: str = "textbook",
    source_credibility: str = "medium",
    existing_ku_summaries: list[str] | None = None,
) -> OntologyExtractResult:
    """Two-pass LLM knowledge ontology extraction.

    Pass 1: chunk → per-chunk metadata → full-book outline
    Pass 2: chunk + outline → 6-class KU candidates + edges + concepts

    All ku_candidates.grade hardcoded to 'unverified'.
    Invalid relation_types silently discarded.
    positional KUs without stance_holder are dropped.
    """
    if not source_text.strip():
        return OntologyExtractResult(
            outline={},
            ku_candidates=[],
            edge_candidates=[],
            concept_candidates=[],
            stats={"total": 0, "by_type": {}, "explains_count": 0},
        )

    chunks = _split_chunks(source_text, chunk_size)

    # ------------------------------------------------------------------
    # Pass 1: per-chunk extraction → outline
    # ------------------------------------------------------------------
    chunk_analyses: list[dict] = []
    for chunk in chunks:
        prompt = _PASS1_CHUNK_TMPL.format(chunk_text=chunk)
        resp = await llm(
            messages=[{"role": "user", "content": prompt}],
            system=_PASS1_CHUNK_SYSTEM,
            max_tokens=512,
        )
        analysis = _parse_json(resp) or {"concepts": [], "topics": [], "chapter": ""}
        chunk_analyses.append(analysis)

    outline_prompt = _PASS1_OUTLINE_TMPL.format(
        doc_type=doc_type,
        source_credibility=source_credibility,
        chunk_analyses=json.dumps(chunk_analyses, ensure_ascii=False, indent=2),
    )
    outline_resp = await llm(
        messages=[{"role": "user", "content": outline_prompt}],
        system=_PASS1_OUTLINE_SYSTEM,
        max_tokens=1024,
    )
    outline = _parse_json(outline_resp) or {
        "chapters": [], "core_concepts": [], "main_thread": "",
        "stance": "", "doc_type": doc_type, "source_credibility": source_credibility,
    }

    # ------------------------------------------------------------------
    # Pass 2: per-chunk KU extraction with outline context
    # ------------------------------------------------------------------
    all_ku_candidates: list[dict] = []
    all_edge_candidates: list[dict] = []
    all_concept_candidates: list[str] = []

    outline_str = json.dumps(outline, ensure_ascii=False, indent=2)

    for chunk_idx, chunk in enumerate(chunks):
        prompt = _PASS2_CHUNK_TMPL.format(
            outline=outline_str,
            chunk_text=chunk,
            six_class_rules=_SIX_CLASS_RULES,
        )
        resp = await llm(
            messages=[{"role": "user", "content": prompt}],
            system=_PASS2_SYSTEM,
            max_tokens=2048,
        )
        data = _parse_json(resp) or {}

        # Collect KU candidates
        for ku in data.get("ku_candidates", []):
            if not isinstance(ku, dict):
                continue
            # Enforce grade = "unverified"
            ku["grade"] = "unverified"
            # Validate knowledge_type
            if ku.get("knowledge_type") not in VALID_KNOWLEDGE_TYPES:
                ku["knowledge_type"] = "factual"
            # positional must have stance_holder
            if ku.get("knowledge_type") == "positional" and not ku.get("stance_holder"):
                continue  # drop KU — violates mandate
            # Reassign unique id
            ku["id"] = f"ku_c{chunk_idx}_{len(all_ku_candidates)}"
            all_ku_candidates.append(ku)

        # Collect edge candidates — discard invalid relation_types
        for edge in data.get("edge_candidates", []):
            if not isinstance(edge, dict):
                continue
            if edge.get("relation_type") not in VALID_RELATION_TYPES:
                continue
            all_edge_candidates.append(edge)

        # Collect concept candidates
        for concept in data.get("concept_candidates", []):
            if isinstance(concept, str) and concept not in all_concept_candidates:
                all_concept_candidates.append(concept)

    # ------------------------------------------------------------------
    # Build stats
    # ------------------------------------------------------------------
    by_type: dict[str, int] = {}
    for ku in all_ku_candidates:
        kt = ku.get("knowledge_type", "unknown")
        by_type[kt] = by_type.get(kt, 0) + 1

    explains_count = sum(
        1 for e in all_edge_candidates if e.get("relation_type") == "explains"
    )

    stats = {
        "total": len(all_ku_candidates),
        "by_type": by_type,
        "explains_count": explains_count,
    }

    return OntologyExtractResult(
        outline=outline,
        ku_candidates=all_ku_candidates,
        edge_candidates=all_edge_candidates,
        concept_candidates=all_concept_candidates,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_chunks(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks of approximately chunk_size characters."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to split at a sentence boundary
            boundary = text.rfind("。", start, end)
            if boundary == -1:
                boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


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
    except (json.JSONDecodeError, ValueError):
        return None
