"""oskill.knowledge — Phase 1 + Phase 10 + Phase 11B knowledge management skills."""
from oskill.knowledge.classify_inbox_file import ClassifyResult, classify_inbox_file
from oskill.knowledge.detect_duplicate_substrate import detect_duplicate_substrate
from oskill.knowledge.generate_audio_narration import AudioNarrationResult, generate_audio_narration
from oskill.knowledge.generate_derivative import generate_derivative
from oskill.knowledge.generate_illustration import IllustrationResult, generate_illustration
from oskill.knowledge.hybrid_search import SearchResult, hybrid_search
from oskill.knowledge.ingest_substrate import IngestResult, ingest_substrate
from oskill.knowledge.lint import LintIssue, lint
from oskill.knowledge.transcribe_audio_substrate import TranscriptionResult, transcribe_audio_substrate
from oskill.knowledge.translate_substrate import TranslateResult, translate_substrate
from oskill.knowledge.web_search_augmented import WebSearchResponse, web_search_augmented

__all__ = [
    "classify_inbox_file", "ClassifyResult",
    "ingest_substrate", "IngestResult",
    "detect_duplicate_substrate",
    "generate_derivative",
    "generate_audio_narration", "AudioNarrationResult",
    "generate_illustration", "IllustrationResult",
    "transcribe_audio_substrate", "TranscriptionResult",
    "web_search_augmented", "WebSearchResponse",
    "hybrid_search", "SearchResult",
    "lint", "LintIssue",
    "translate_substrate", "TranslateResult",
]
