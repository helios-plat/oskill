"""oskill.knowledge — Phase 1 knowledge management skills."""
from oskill.knowledge.classify_inbox_file import ClassifyResult, classify_inbox_file
from oskill.knowledge.detect_duplicate_substrate import detect_duplicate_substrate
from oskill.knowledge.generate_derivative import generate_derivative
from oskill.knowledge.hybrid_search import SearchResult, hybrid_search
from oskill.knowledge.ingest_substrate import IngestResult, ingest_substrate
from oskill.knowledge.lint import LintIssue, lint

__all__ = [
    "classify_inbox_file", "ClassifyResult",
    "ingest_substrate", "IngestResult",
    "detect_duplicate_substrate",
    "generate_derivative",
    "hybrid_search", "SearchResult",
    "lint", "LintIssue",
]
