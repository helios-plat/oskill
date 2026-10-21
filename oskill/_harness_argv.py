"""oskill.harness_argv — engine name + prompt → argv. Pure function, no I/O."""

from __future__ import annotations

from typing import Any

HARNESS_ENGINES = ("claude", "codex", "pi", "dsh", "grok", "opencode")


def harness_argv(
    engine: str,
    prompt: str,
    *,
    model: str | None = None,
    streaming: bool = False,
    bin: str | None = None,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    """Build a no-shell argv for a coding harness.

    ``master`` is not a harness. Container-specific path/probe logic stays in Veya.
    """
    name = (engine or "").strip().lower()
    if name == "master":
        return {
            "ok": False,
            "engine": name,
            "argv": [],
            "error": "master is the product ReAct loop, not a harness",
        }
    if name not in HARNESS_ENGINES:
        return {
            "ok": False,
            "engine": name,
            "argv": [],
            "error": f"unknown harness {engine!r}; expected one of {list(HARNESS_ENGINES)}",
        }
    exe = bin or name
    if name == "claude":
        argv = [exe, "-p", prompt]
        if streaming:
            argv += ["--output-format", "stream-json", "--verbose"]
        if model:
            argv += ["--model", model]
    elif name == "codex":
        argv = [
            exe,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            prompt,
        ]
        if model:
            argv += ["-m", model]
    elif name == "pi":
        argv = [exe, "-p", prompt]
        if model:
            argv += ["--model", model]
    elif name == "dsh":
        argv = [exe, "--profile", "headless", prompt]
    elif name == "grok":
        argv = [exe, "-p", prompt]
        if streaming:
            argv += ["--output-format", "streaming-messages-json"]
        if model:
            argv += ["--model", model]
    else:
        argv = [exe, "run", prompt, "--model", model or "opencode-go/deepseek-v4-flash"]
    if extra:
        argv.extend(extra)
    return {"ok": True, "engine": name, "argv": argv, "error": ""}
