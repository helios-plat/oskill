"""oskill.isolation_policy — purpose → isolation/image. Pure function, no I/O."""

from __future__ import annotations

from typing import Any

_POLICIES: dict[str, dict[str, Any]] = {
    "chat_verify": {
        "isolation": "process",
        "image": "",
        "block_network": False,
        "cpu": "1",
        "memory": "512m",
        "note": "process limits only; network is NOT blocked",
    },
    "untrusted_exec": {
        "isolation": "docker",
        "image": "python:3.11-slim",
        "block_network": True,
        "cpu": "1",
        "memory": "512m",
        "note": "docker --network=none",
    },
    "pytest_eval": {
        "isolation": "docker",
        "image": "veya-code-sandbox:latest",
        "block_network": True,
        "cpu": "1",
        "memory": "512m",
        "note": "docker pytest image",
    },
    "pytest_local": {
        "isolation": "process",
        "image": "",
        "block_network": False,
        "cpu": "1",
        "memory": "512m",
        "note": "explicit local pytest; not isolated from the network",
    },
    "video_eval": {
        "isolation": "docker",
        "image": "veya-video-sandbox:latest",
        "block_network": True,
        "cpu": "1",
        "memory": "1g",
        "note": "docker video eval image",
    },
    "tree_search": {
        "isolation": "netns",
        "image": "",
        "block_network": True,
        "cpu": "1",
        "memory": "512m",
        "note": "unshare -Urn",
    },
    "harness_run": {
        "isolation": "docker",
        "image": "veya-sandbox-tools:latest",
        "block_network": False,
        "cpu": "2",
        "memory": "2g",
        "note": "harness needs egress to model APIs",
    },
    "harness_host": {
        "isolation": "process",
        "image": "",
        "block_network": False,
        "cpu": "2",
        "memory": "2g",
        "note": "host CLI in process sandbox; caller workspace is not deleted",
    },
    "hicode_workspace": {
        "isolation": "process",
        "image": "",
        "block_network": False,
        "cpu": "2",
        "memory": "2g",
        "note": "path-jail on host workspace; docker optional later",
    },
    "memory_test": {
        "isolation": "memory",
        "image": "",
        "block_network": False,
        "cpu": "1",
        "memory": "512m",
        "note": "in-process fixture backend",
    },
}

# Hosted/multi-user: never process-jail on the app host. OpenSandbox is the
# execution plane; egress denied until an explicit policy opens it.
_HOSTED: dict[str, dict[str, Any]] = {
    "chat_verify": {
        "isolation": "opensandbox",
        "image": "python:3.11-slim",
        "block_network": True,
        "cpu": "1",
        "memory": "512m",
        "note": "hosted: OpenSandbox; egress denied by default",
    },
    "hicode_workspace": {
        "isolation": "opensandbox",
        "image": "python:3.11-slim",
        "block_network": True,
        "cpu": "2",
        "memory": "2g",
        "note": "hosted: per-user OpenSandbox volume, not host path-jail",
    },
    "pytest_local": {
        "isolation": "opensandbox",
        "image": "python:3.11-slim",
        "block_network": True,
        "cpu": "1",
        "memory": "512m",
        "note": "hosted: pytest_local upgraded off process",
    },
    "harness_host": {
        "isolation": "docker",
        "image": "veya-sandbox-tools:latest",
        "block_network": False,
        "cpu": "2",
        "memory": "2g",
        "note": "hosted: harness_host upgraded off process",
    },
}


def isolation_policy(purpose: str, profile: str = "local") -> dict[str, Any]:
    """Return a copy of the isolation policy for ``purpose``.

    ``profile`` is ``local`` (single-user laptop) or ``hosted`` (multi-user).
    Pure: no env/I/O. The assembly layer supplies the profile.
    """
    spec = _POLICIES.get(purpose)
    if spec is None:
        return {
            "ok": False,
            "error": f"unknown purpose {purpose!r}; expected one of {sorted(_POLICIES)}",
        }
    kind = (profile or "local").strip().lower()
    if kind == "hosted":
        spec = _HOSTED.get(purpose, spec)
        if spec.get("isolation") == "process":
            return {
                "ok": False,
                "error": (
                    f"hosted profile forbids process isolation for purpose {purpose!r}"
                ),
                "purpose": purpose,
                "profile": "hosted",
            }
    out = dict(spec)
    out["ok"] = True
    out["purpose"] = purpose
    out["profile"] = kind if kind == "hosted" else "local"
    return out
