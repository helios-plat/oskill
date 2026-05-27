"""Shared Pydantic models for Hevi video generation oskill."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Scene(BaseModel):
    """A single scene in a video script."""

    index: int
    narration: str
    duration_s: float
    visual_description: str


class Script(BaseModel):
    """Video script output from script_writer."""

    title: str
    description: str
    scenes: list[Scene]
    estimated_duration_s: float


class Shot(BaseModel):
    """A single shot in a storyboard."""

    shot_id: str
    scene_index: int
    visual_description: str
    narration: str
    duration_s: float
    importance: int = 0
    motion: str | None = None


class Storyboard(BaseModel):
    """Storyboard output from storyboard_planner."""

    shots: list[Shot]


class ShotPlan(BaseModel):
    """Per-shot generation plan."""

    shot_id: str
    image_prompt: str
    tts_text: str
    duration_s: float


class ConsistencyIssue(BaseModel):
    """A single consistency issue found."""

    shot_id: str
    description: str
    severity: str = "medium"


class ConsistencyReport(BaseModel):
    """Consistency check output."""

    issues: list[ConsistencyIssue]
    overall_score: float


class ReferenceDescription(BaseModel):
    """Detailed image generation prompt for a shot."""

    shot_id: str
    detailed_prompt: str
    style_tags: list[str]


class MetadataConstraints(BaseModel):
    """Platform-agnostic metadata constraints."""

    title_max_chars: int
    description_max_chars: int
    tags_max_count: int
    tag_max_chars: int


class Metadata(BaseModel):
    """Generated metadata output."""

    title: str
    description: str
    tags: list[str]
    topics: list[str]


class InsightContext(BaseModel):
    """Output from threeo_ingester."""

    topic: str
    key_findings: list[str]
    charts: list[dict[str, object]]
    related_concepts: list[str]
    source_omodul: str
    raw_report: dict[str, object]


class SubjectRef(BaseModel):
    """Reference to a subject/character for LLM prompt injection.

    Used by script_writer, storyboard_planner, and multi_shot_storyboard_workflow
    to inject character context into LLM prompts.
    """

    subject_id: str
    name: str
    description: str = ""  # optional; injected into LLM prompt when non-empty
    image_path: Path | None = None  # optional reference image
