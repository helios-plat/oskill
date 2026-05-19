"""Tests for translate_substrate skill."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from oprim.meta_db import open_meta_db
from oprim.translate.protocol import TranslationResult
from oskill.knowledge.translate_substrate import TranslateResult, translate_substrate


def _make_mock_provider(reply: str = "翻译内容"):
    prov = MagicMock()
    prov.name = "mock"
    prov.translate.return_value = TranslationResult(
        text=reply,
        provider="mock",
        model="mock",
        input_tokens=10,
        output_tokens=10,
        cost_usd=0.001,
        source_lang="en",
        target_lang="zh",
    )
    return prov


def _seed_substrate(db_path: Path, substrate_id: str, markdown_text: str) -> None:
    import oprim.meta_db as _mod
    migrations_dir = Path(_mod.__file__).parent / "migrations"
    db = open_meta_db(db_path)
    db.migrate(migrations_dir)
    db.execute(
        """INSERT INTO substrate (id, ulid, title, meta_json, created_at, updated_at)
           VALUES (?, ?, ?, '{}', current_timestamp, current_timestamp)""",
        [substrate_id, substrate_id, "Test"],
    )
    from ulid import ULID
    deriv_id = str(ULID())
    db.execute(
        "INSERT INTO derivative (id, substrate_id, kind, content) VALUES (?,?,?,?)",
        [deriv_id, substrate_id, "markdown", markdown_text],
    )
    db.close()


def test_translate_substrate_basic(stratum_home):
    db_path = stratum_home / "meta.duckdb"
    substrate_id = "01SUBSTRATE_TEST001"
    _seed_substrate(db_path, substrate_id, "Hello world. This is a test.")

    mock_prov = _make_mock_provider("你好世界。这是一个测试。")

    with patch("oskill.knowledge.translate_substrate.translate_document") as mock_td:
        mock_td.return_value = (
            "你好世界。这是一个测试。",
            [TranslationResult(
                text="你好世界。",
                provider="mock",
                model="mock",
                input_tokens=10,
                output_tokens=8,
                cost_usd=0.001,
                source_lang="en",
                target_lang="zh",
            )],
        )
        result = translate_substrate(substrate_id, "zh", provider="deepseek")

    assert isinstance(result, TranslateResult)
    assert result.substrate_id == substrate_id
    assert result.target_lang == "zh"
    assert result.chunks_translated == 1
    assert result.derivative_id != ""

    db = open_meta_db(db_path)
    rows = db.execute(
        "SELECT kind, content FROM derivative WHERE id = ?",
        [result.derivative_id],
    ).fetchall()
    db.close()
    assert len(rows) == 1
    assert rows[0][0] == "translation_zh"
    assert "你好世界" in rows[0][1]


def test_translate_substrate_idempotent_no_overwrite(stratum_home):
    db_path = stratum_home / "meta.duckdb"
    substrate_id = "01SUBSTRATE_IDEM001"
    _seed_substrate(db_path, substrate_id, "Some text.")

    with patch("oskill.knowledge.translate_substrate.translate_document") as mock_td:
        mock_td.return_value = ("译文", [])
        r1 = translate_substrate(substrate_id, "zh", provider="deepseek")
        r2 = translate_substrate(substrate_id, "zh", provider="deepseek")

    assert r1.derivative_id == r2.derivative_id
    mock_td.assert_called_once()


def test_translate_substrate_not_found(stratum_home):
    db_path = stratum_home / "meta.duckdb"
    import oprim.meta_db as _mod
    db = open_meta_db(db_path)
    db.migrate(Path(_mod.__file__).parent / "migrations")
    db.close()

    from oprim.errors import StratumError
    with pytest.raises(StratumError, match="Substrate not found"):
        translate_substrate("NONEXISTENT_ID", "zh")


def test_translate_substrate_no_db(tmp_path, monkeypatch):
    import oprim._config as _cfg_mod
    monkeypatch.setenv("STRATUM_HOME", str(tmp_path / "empty_stratum"))
    _cfg_mod._store["STRATUM_HOME"] = str(tmp_path / "empty_stratum")

    from oprim.errors import StratumError
    with pytest.raises(StratumError, match="MetaDB not found"):
        translate_substrate("ANY_ID", "zh")

    _cfg_mod._store.pop("STRATUM_HOME", None)


def test_translate_result_cost_aggregation(stratum_home):
    db_path = stratum_home / "meta.duckdb"
    substrate_id = "01SUBSTRATE_COST001"
    _seed_substrate(db_path, substrate_id, "Paragraph one.\n\nParagraph two.")

    chunks = [
        TranslationResult("一", "mock", "mock", 10, 8, 0.001, "en", "zh"),
        TranslationResult("二", "mock", "mock", 12, 9, 0.002, "en", "zh"),
    ]
    with patch("oskill.knowledge.translate_substrate.translate_document") as mock_td:
        mock_td.return_value = ("一 二", chunks)
        result = translate_substrate(substrate_id, "zh", provider="deepseek")

    assert result.chunks_translated == 2
    assert result.total_tokens_in == 22
    assert result.total_tokens_out == 17
    assert abs(result.cost_usd - 0.003) < 1e-9
