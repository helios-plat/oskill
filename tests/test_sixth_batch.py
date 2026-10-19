"""Tests for runtime_backends / doc_extractors / memory_system / test_report /
provider_clients / md_to_wechat_html 增强 (第六轮深挖)。"""

from __future__ import annotations

import pytest

from oskill.doc_extractors import (
    DataSourceAdapter,
    extract_docx,
    extract_text,
    extract_xlsx,
)
from oskill.memory_system import (
    MEMORY_RAG,
    MEMORY_TOOL,
    MemoryStore,
    ToolMemory,
)
from oskill.provider_clients import (
    PROVIDER_REGISTRY,
    ProviderClient,
    client_for,
)
from oskill.runtime_backends import (
    BackendExecutor,
    BackendRegistry,
    RuntimeBackend,
    _default_registry,
)
from oskill.test_report import (
    STATUS_SKIPPED,
    TestCaseResult,
    collect_test_run,
    skipped_case,
)
from oskill.wechat_publish import md_to_wechat_html

# ── runtime_backends ────────────────────────────────────────────────


def test_registry_register_and_capabilities():
    registry = _default_registry()
    assert set(registry.list_backends()) == {
        "fast-shell",
        "structured-module",
        "isolated-container",
    }
    caps = registry.capabilities()
    assert caps["counts"]["fast_path"] == 1


def test_select_by_capability():
    registry = _default_registry()
    selected = registry.select(require=["structured_output"])
    assert selected == ["structured-module"]
    isolated = registry.select(kind="container", require=["fs_sync"])
    assert isolated == ["isolated-container"]


def test_select_prefers_fast_path():
    registry = BackendRegistry()
    registry.register(RuntimeBackend("a", capabilities=["network"]))
    registry.register(RuntimeBackend("b", capabilities=["network", "fast_path"]))
    selected = registry.select(require=["network"], prefer=["fast_path"])
    assert selected[0] == "b"


def test_backend_executor_lazy_init():
    init_calls = {"n": 0}
    calls = {"n": 0}

    def init():
        init_calls["n"] += 1

    def exec_fn(source, options):
        calls["n"] += 1
        return {"ok": True, "source": source}

    registry = BackendRegistry()
    registry.register(RuntimeBackend("b", init=init, exec=exec_fn))
    executor = BackendExecutor(registry)
    result = executor.execute("echo hi", backend_id="b")
    assert result["ok"] is True
    assert init_calls["n"] == 1
    executor.execute("x", backend_id="b")
    assert init_calls["n"] == 1  # 懒连接只初始化一次


def test_executor_selects_by_requirement():
    registry = BackendRegistry()
    registry.register(RuntimeBackend("plain", capabilities=[]))
    registry.register(
        RuntimeBackend(
            "structured", capabilities=["structured_output"], exec=lambda s, o: {"ok": True}
        )
    )
    executor = BackendExecutor(registry)
    result = executor.execute("x", require=["structured_output"])
    assert result["ok"] is True


# ── doc_extractors ──────────────────────────────────────────────────


def test_extract_docx(tmp_path):
    # 构造最小 docx (zip + document.xml)
    import zipfile

    docx_path = tmp_path / "test.docx"
    doc_xml = (
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>'
        "<w:p><w:r><w:t>Hello</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>World</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", doc_xml)
    text = extract_docx(docx_path)
    assert "Hello" in text and "World" in text


def test_extract_xlsx(tmp_path):
    import zipfile

    xlsx_path = tmp_path / "test.xlsx"
    sheet_xml = (
        '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData>'
        '<row><c t="s"><v>0</v></c><c><v>42</v></c></row>'
        "</sheetData></worksheet>"
    )
    shared = (
        '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><si><t>商品</t></si></sst>'
    )
    with zipfile.ZipFile(xlsx_path, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    text = extract_xlsx(xlsx_path)
    assert "商品" in text and "42" in text


def test_datasource_adapter_supported():
    adapter = DataSourceAdapter()
    assert ".docx" in adapter.supported()
    assert ".pdf" in adapter.supported()
    with pytest.raises(ValueError, match="unsupported format"):
        adapter.extract("file.xyz")


def test_extract_txt(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    assert extract_text(f) == "hello"


# ── memory_system ──────────────────────────────────────────────────


def test_memory_store_remember_recall():
    store = MemoryStore()
    store.remember(MEMORY_TOOL, "web", "用 urllib 抓网页", tags=["网络"])
    assert store.recall(MEMORY_TOOL)[0].key == "web"
    assert store.summary()[MEMORY_TOOL] == 1


def test_memory_store_search():
    store = MemoryStore()
    store.remember(MEMORY_TOOL, "parse", "用 ast 解析 python")
    store.remember(MEMORY_RAG, "chunk", "按段落切分")
    hits = store.search("python")
    assert hits and hits[0].key == "parse"


def test_memory_unknown_kind():
    store = MemoryStore()
    with pytest.raises(ValueError, match="unknown memory kind"):
        store.remember("nope", "k", "v")


def test_tool_memory_recommend():
    tool_memory = ToolMemory()
    tool_memory.learn("解析 python", "ast")
    assert tool_memory.recommend("用 ast 解析这个 python 文件") == "ast"
    assert tool_memory.recommend("写个网页") is None


# ── test_report ────────────────────────────────────────────────────


def test_collect_test_run_mixed():
    def good():
        return TestCaseResult(name="a")

    def bad():
        raise AssertionError("boom")

    def skip():
        return TestCaseResult(name="c", status=STATUS_SKIPPED)

    report = collect_test_run(
        "suite1", {"a": good, "b": bad, "c": skip}, log_command=lambda s: f"[log] {s}"
    )
    assert report.ok is False
    assert len(report.passed) == 1
    assert len(report.failed) == 1
    assert len(report.skipped) == 1
    assert report.failed[0].error.startswith("AssertionError")
    assert report.command_log
    assert "1 passed, 1 failed, 1 skipped" in report.summary_line()


def test_collect_test_run_all_pass():
    report = collect_test_run("suite2", {"a": lambda: TestCaseResult(name="a")})
    assert report.ok is True
    assert report.to_dict()["passed"] == 1


def test_skipped_case():
    result = skipped_case("no network")
    assert result.status == STATUS_SKIPPED


# ── provider_clients ───────────────────────────────────────────────


def test_provider_registry_known():
    for provider in (
        "openai",
        "anthropic",
        "deepseek",
        "zhipu",
        "dashscope",
        "moonshot",
        "openrouter",
        "groq",
        "cerebras",
        "mistral",
    ):
        assert provider in PROVIDER_REGISTRY


def test_client_for_unknown():
    with pytest.raises(ValueError, match="unknown provider"):
        client_for("nope", "key")


def test_client_for_known_config():
    client = client_for("deepseek", "sk-x")
    assert client.base_url == "https://api.deepseek.com/v1"
    assert client.format == "openai"


def test_provider_client_post(monkeypatch):
    """mock httpx: chat_completion 发真实格式请求。"""
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        @property
        def text(self):
            return '{"choices": [{"message": {"content": "ok"}}]}'

    def fake_post(url, **kw):
        captured["url"] = url
        captured["body"] = kw.get("content", b"").decode()
        return _Resp()

    monkeypatch.setattr("httpx.post", fake_post)
    client = ProviderClient("openai", "sk-x")
    result = client.chat_completion("gpt-4o-mini", [{"role": "user", "content": "hi"}])
    assert "chat/completions" in captured["url"]
    assert '"model": "gpt-4o-mini"' in captured["body"]
    assert result["choices"][0]["message"]["content"] == "ok"


# ── md_to_wechat_html 增强 ─────────────────────────────────────────


def test_md_table():
    html_text = md_to_wechat_html("| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert "<table>" in html_text
    assert "<td>1</td>" in html_text


def test_md_task_list():
    html_text = md_to_wechat_html("- [x] 完成\n- [ ] 待办\n")
    assert "checked" in html_text
    assert '<input type="checkbox"' in html_text


def test_md_code_language():
    html_text = md_to_wechat_html("```python\nprint(1)\n```\n")
    assert 'class="language-python"' in html_text


def test_md_enhanced_keeps_basics():
    html_text = md_to_wechat_html("# 标题\n\n正文\n\n- item\n")
    assert "<h1>标题</h1>" in html_text
    assert "<p>正文</p>" in html_text
    assert "<li>item</li>" in html_text
