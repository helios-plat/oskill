"""Public data contracts for video-generation skills.

The concrete Pydantic definitions remain shared internally, while consumers
import this stable flat module instead of the private implementation path.
"""

from oskill._schemas import (
    Chapter,
    ChapterScript,
    ConsistencyIssue,
    ConsistencyReport,
    FrameConsistencyResult,
    InsightContext,
    Metadata,
    MetadataConstraints,
    ReferenceDescription,
    ReferenceSet,
    Scene,
    Script,
    Shot,
    ShotFrame,
    ShotPlan,
    SpeakerLine,
    Storyboard,
    SubjectRef,
)

__all__ = [
    "Chapter",
    "ChapterScript",
    "ConsistencyIssue",
    "ConsistencyReport",
    "FrameConsistencyResult",
    "InsightContext",
    "Metadata",
    "MetadataConstraints",
    "ReferenceDescription",
    "ReferenceSet",
    "Scene",
    "Script",
    "Shot",
    "ShotFrame",
    "ShotPlan",
    "SpeakerLine",
    "Storyboard",
    "SubjectRef",
]
