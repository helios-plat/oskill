import importlib.util
import sys
from unittest.mock import MagicMock


def _mock_deep(name: str) -> MagicMock:
    """Mock a module and all its parent packages."""
    mock = MagicMock()
    sys.modules[name] = mock
    parts = name.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[:i])
        if parent not in sys.modules:
            sys.modules[parent] = MagicMock()
    return mock


# Mock optional/heavy dependencies that are not installed in the dev venv
_HEAVY_DEPS = [
    "paramiko",
    "fsrs",
    "frontmatter",
    "dashscope",
    "lancedb",
    "duckdb",
    "tantivy",
    "fitz",
    "pymupdf",
    "pymupdf4llm",
    "magic",
    "ulid",
    "ebooklib",
    "docker",
    "docker.errors",
    "boto3",
    "botocore",
    "botocore.exceptions",
    "dns",
    "dns.resolver",
    "redis",
    "readability",
    "akshare",
    "stripe",
    "google",
    "google.oauth2",
    "google.auth",
    "google.auth.transport",
    "googleapiclient",
    "googleapiclient.discovery",
    "alipay",
    "python_alipay_sdk",
]

def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


# Only stub what is genuinely missing. Stubbing an installed dependency (e.g. duckdb,
# python-magic, lancedb via oprim[storage]) silently turns real-backend tests into
# MagicMock soup ("Object of type MagicMock is not JSON serializable", empty fetchall()).
for _mod in _HEAVY_DEPS:
    if not _importable(_mod):
        _mock_deep(_mod)
