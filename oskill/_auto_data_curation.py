"""oskill.auto_data_curation — 基于 dlt 数据推导的信息整理归一化技能.

Stateless 纯算法。依赖 normalize_op + pipeline_store 注入.

组合: normalize_op (注入) + pipeline_store (注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

from typing import Any, Protocol


class NormalizeProtocol(Protocol):
    """数据规范化器 Protocol."""

    def __call__(
        self,
        raw_json_data: list[dict[str, Any]],
        *,
        pipeline_op: Any = None,
    ) -> dict[str, Any]: ...


class PipelineStoreProtocol(Protocol):
    """DLT 管道存储 Protocol."""

    def auto_infer_and_load(
        self, table_name: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]: ...


def auto_data_curation(
    unstructured_data_list: list[dict[str, Any]],
    *,
    normalize_op: NormalizeProtocol,
    pipeline_store: PipelineStoreProtocol,
) -> dict[str, Any]:
    """基于 dlt 数据推导将杂乱半结构化信息自动归一化整理为数据库 Schema 表.

    流程:
    1. 调用 normalize_op 规范化字段名与值
    2. 调用 pipeline_store 自动推导 Schema 并入库存

    Args:
        unstructured_data_list: 半结构化数据列表
        normalize_op: 数据规范化器（注入）
        pipeline_store: DLT 管道存储（注入）

    Returns:
        {
            "status": "curated" | "failed",
            "processed_records": int,
            "inferred_schema_sample": dict,
        }
    """
    if not unstructured_data_list:
        return {
            "status": "curated",
            "processed_records": 0,
            "inferred_schema_sample": {},
        }

    try:
        # Step 1: 规范化
        norm_res = normalize_op(
            unstructured_data_list,
            pipeline_op=pipeline_store,
        )
    except Exception as e:
        return {
            "status": "failed",
            "processed_records": 0,
            "inferred_schema_sample": {},
            "error": f"Normalization failed: {type(e).__name__}: {e}",
        }

    return {
        "status": "curated",
        "processed_records": norm_res.get("count", 0),
        "inferred_schema_sample": norm_res.get("sample_record", {}),
    }
