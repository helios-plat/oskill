"""Shared path resolution for knowledge skills."""

from __future__ import annotations
from pathlib import Path
from oprim._config import cfg


def stratum_home() -> Path:
    return Path(cfg.get("STRATUM_HOME", str(Path.home() / ".stratum")))


def meta_db_path() -> Path:
    return stratum_home() / "meta.duckdb"


def meta_db_enabled() -> bool:
    """本地 DuckDB meta_db 是否启用。

    ★2026-07-10: stratum 后端早已把 substrates/derivative 迁到 Postgres(经
    stratum.db.get_conn), 但 oskill 的 ingest_substrate/detect_duplicate 仍写/读这个
    DuckDB meta_db——迁移后表已不存在, 于是每条入库的 meta_db 写全部报错(Catalog Error:
    Table substrates does not exist), 且 detect_duplicate 静默返回 None(去重假阴性, 重复
    件照样入库)。当消费方(stratum source_watcher/folder_watcher)已在 PG 侧自己做
    file_hash 去重时, 应把这个 DuckDB 层整体关掉。
    默认启用(=历史行为不变), 由部署方按需 OSKILL_META_DB_ENABLED=0 关闭。
    """
    return str(cfg.get("OSKILL_META_DB_ENABLED", "1")).lower() not in ("0", "false", "no")


def tantivy_path() -> Path:
    return stratum_home() / "index" / "tantivy"


def lancedb_path() -> Path:
    return stratum_home() / "index" / "lance"


def substrate_data_path() -> Path:
    return stratum_home() / "data" / "substrate"
