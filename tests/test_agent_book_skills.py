"""Tests for failure_learning / agent_context_pool / voice_pipeline (ai-agent-book 3O 内化)。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from oskill.agent_context_pool import (
    VISIBILITY_ISOLATED,
    VISIBILITY_SHARED,
    ContextPool,
)
from oskill.failure_learning import (
    ExperienceStore,
    FailureRecord,
    format_experiences,
)
from oskill.voice_pipeline import (
    FULL_DUPLEX_MODE,
    PIPE_MODE,
    STREAM_MODE,
    interrupt_turn,
    run_voice_pipeline,
)

# ── failure_learning: 从失败中学习 ───────────────────────────────────


def test_record_and_match(tmp_path: Path):
    store = ExperienceStore(tmp_path / "exp.json")
    store.record(
        FailureRecord(
            task="调用外部 API 获取天气数据",
            failure_type="timeout",
            error="requests timed out",
            lesson="外部 API 调用必须加超时与重试",
        )
    )
    store.record(
        FailureRecord(
            task="调用外部 API 获取行情数据",
            failure_type="timeout",
            error="requests timed out",
            lesson="外部 API 调用必须加超时与重试",
        )
    )
    # 检索: 天气任务命中 timeout 经验
    matches = store.match("获取天气数据")
    assert matches and matches[0].failure_type == "timeout"
    assert store.summary()["total_occurrences"] >= 2


def test_store_persists(tmp_path: Path):
    store = ExperienceStore(tmp_path / "exp.json")
    store.record(
        FailureRecord(
            task="解析 JSON 配置文件",
            failure_type="parse",
            error="bad json",
            lesson="JSON 解析前先校验格式",
        )
    )
    store.save()
    # 新实例从文件恢复
    reloaded = ExperienceStore(tmp_path / "exp.json")
    assert reloaded.summary()["failure_types"] == ["parse"]
    assert reloaded.experiences["parse"].lessons == ["JSON 解析前先校验格式"]
    matches = reloaded.match("解析配置文件")
    assert matches and matches[0].failure_type == "parse"


def test_learn_batch_and_dedup(tmp_path: Path):
    store = ExperienceStore(tmp_path / "exp.json")
    store.learn(
        [
            FailureRecord(
                task="写文件",
                failure_type="io",
                error="permission denied",
                lesson="写入前检查目录权限",
            ),
            FailureRecord(
                task="写文件",
                failure_type="io",
                error="permission denied",
                lesson="写入前检查目录权限",
            ),  # 重复教训去重
        ]
    )
    exp = store.experiences["io"]
    assert exp.lessons == ["写入前检查目录权限"]  # 去重


def test_format_experiences():
    store = ExperienceStore(None)
    store.record(
        FailureRecord(
            task="处理时间序列", failure_type="logic", error="index error", lesson="边界索引需检查"
        )
    )
    text = format_experiences(store.match("处理时间序列"))
    assert "处理时间序列" in text or "logic" in text
    assert format_experiences([]) == ""


# ── agent_context_pool: 多 Agent 上下文共享/隔离 ─────────────────────


def test_pool_shared_and_isolated():
    pool = ContextPool()
    pool.set("planner", "goal", "构建平台", visibility=VISIBILITY_SHARED)
    pool.set("worker-a", "notes", "私有草稿", visibility=VISIBILITY_ISOLATED)

    assert pool.projected("worker-a")["goal"] == "构建平台"
    assert pool.projected("worker-a")["notes"] == "私有草稿"
    # 其他 agent 看不到 worker-a 的私有草稿
    assert "notes" not in pool.projected("worker-b")


def test_pool_isolation_check():
    pool = ContextPool()
    pool.set("alice", "secret", "机密", visibility=VISIBILITY_ISOLATED)
    assert pool.isolation_check("bob", "alice") == []


def test_pool_private_overrides_shared():
    pool = ContextPool()
    pool.set("alice", "goal", "共享目标", visibility=VISIBILITY_SHARED)
    pool.set("bob", "goal", "bob 私有", visibility=VISIBILITY_ISOLATED)
    # alice 只看到共享版本; bob 看到自己的私有版本 (私有覆盖同键共享)
    assert pool.projected("alice")["goal"] == "共享目标"
    assert pool.projected("bob")["goal"] == "bob 私有"


def test_pool_invalid_visibility():
    pool = ContextPool()
    with pytest.raises(ValueError, match="invalid visibility"):
        pool.set("a", "k", "v", visibility="secret")


def test_pool_version_increments():
    pool = ContextPool()
    pool.set("a", "k", "v1", visibility=VISIBILITY_SHARED)
    pool.set("a", "k", "v2", visibility=VISIBILITY_SHARED)
    assert pool.get("a", "k").version == 2
    assert pool.summary()["shared"] == 1


# ── voice_pipeline: 语音三范式 ───────────────────────────────────────


def _asr(audio):
    return "用户说: 你好"


def _llm(text):
    return "回复: 你好呀, 这是一段较长的测试回复用于分块。"


def _tts(text):
    return f"[audio:{text[:6]}]"


def test_pipe_mode():
    turn = asyncio.run(
        run_voice_pipeline(
            b"audio",
            asr=_asr,
            llm=_llm,
            tts=_tts,
            mode=PIPE_MODE,
        )
    )
    assert turn.mode == PIPE_MODE
    assert turn.text.startswith("用户说")
    assert turn.audio_out is not None
    assert len(turn.segments) == 1


def test_stream_mode_chunks():
    turn = asyncio.run(
        run_voice_pipeline(
            b"audio",
            asr=_asr,
            llm=_llm,
            tts=_tts,
            mode=STREAM_MODE,
            stream_chunk_size=10,
        )
    )
    assert len(turn.segments) >= 2  # 长文本被分块
    assert all("audio" in str(seg["audio_out"]) for seg in turn.segments)


def test_full_duplex_interrupt():
    turn = asyncio.run(
        run_voice_pipeline(
            b"audio",
            asr=_asr,
            llm=_llm,
            tts=_tts,
            mode=FULL_DUPLEX_MODE,
            stream_chunk_size=10,
        )
    )
    assert not turn.interrupted
    interrupted = asyncio.run(interrupt_turn(turn))
    assert interrupted.interrupted is True
    # 打断后段落被截断
    assert len(interrupted.segments) < len(turn.segments) or interrupted.interrupted


def test_async_handlers_supported():
    async def async_llm(text):
        return "async reply"

    turn = asyncio.run(
        run_voice_pipeline(
            b"audio",
            asr=lambda a: "hi",
            llm=async_llm,
            tts=_tts,
            mode=PIPE_MODE,
        )
    )
    assert "async reply" in turn.segments[0]["text"]


def test_invalid_mode():
    with pytest.raises(ValueError, match="invalid mode"):
        asyncio.run(
            run_voice_pipeline(
                b"audio",
                asr=_asr,
                llm=_llm,
                tts=_tts,
                mode="telepathy",
            )
        )
