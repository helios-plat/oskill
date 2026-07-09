"""K-XX qmd_bridge — retrieve/deep_read/dedup_prefilter over qmd (MinerU-Document-Explorer).

MINERU-AII-INTEGRATION-SPEC-001 §3.3. qmd only does retrieval/chunking/location —
it does NOT produce KUs (red line R1). Semantic judgment (what a claim's inner
essence is, whether it's proven) always stays in AII omodul; this module is a
thin IO bridge to qmd's MCP tools, nothing more.

Composes: raw aiohttp calls to qmd's MCP Streamable-HTTP endpoint (see
aii/docker-compose.aii-qmd.yml — network_mode: host, port 8181, corpus mounted
read-only at /corpus, collection name "aii-books").

Two real pitfalls found running this against the actual container (not just
documented, empirically hit):
  1. The MCP server rejects requests whose Host header isn't literally
     "localhost" (silent connection reset, no error body) — this is why the
     URL below is http://localhost:8181/mcp and NOT 127.0.0.1. It also only
     accepts connections through Docker's `network_mode: host` (published
     ports via the userland-proxy/NAT path get the same silent reset).
  2. `qmd embed` (bulk-embeds the corpus for vector/hyde search) and `query`
     calls appear to contend for the same resource (SQLite lock or CPU — not
     root-caused) — `query` can hang indefinitely while a bulk embed job is
     running. Pure `lex` (BM25) queries are unaffected once embed isn't
     mid-run. Not this module's problem to solve; documented for whoever next
     debugges "query() hangs forever."

IO-orchestration (MCP network call). Stateless — opens+closes a fresh MCP
session per call (initialize -> notifications/initialized -> tools/call)
rather than holding a persistent one; qmd call volume in the current
pipeline is low enough that the extra round-trips don't matter. If that
changes, a persistent-session variant is the obvious next step.
"""

from __future__ import annotations

import json
from typing import Any

import aiohttp

QMD_MCP_URL = "http://localhost:8181/mcp"
_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "aii-oskill-qmd-bridge", "version": "0.1.0"}


class QmdBridgeError(Exception):
    """qmd MCP call failed (transport, protocol, or tool-reported error)."""


async def _mcp_call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Open a fresh MCP session against qmd, call one tool, return structuredContent.

    Raises:
        QmdBridgeError: Transport failure, malformed response, or the tool
            itself reported isError.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                QMD_MCP_URL,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": _PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": _CLIENT_INFO,
                    },
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                session_id = resp.headers.get("mcp-session-id")
                if resp.status != 200 or not session_id:
                    raise QmdBridgeError(
                        f"qmd initialize failed: http={resp.status} session_id={session_id!r}"
                    )

            init_headers = {**headers, "mcp-session-id": session_id}
            async with session.post(
                QMD_MCP_URL,
                headers=init_headers,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 202:
                    raise QmdBridgeError(
                        f"qmd notifications/initialized failed: http={resp.status}"
                    )

            async with session.post(
                QMD_MCP_URL,
                headers=init_headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
                # 120s not 60s: this host runs CPU-only inference (no GPU) on an
                # already-busy shared machine (load avg ~25 observed during
                # testing) — a cold hybrid query (expansion + rerank models
                # loading/competing for CPU) empirically took >60s at least
                # once, then 3.5s once warm. Generous timeout > tight one here.
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    raise QmdBridgeError(f"qmd tools/call '{name}' failed: http={resp.status}")
                body = await resp.json()
        except aiohttp.ClientError as exc:
            raise QmdBridgeError(f"qmd transport error calling '{name}': {exc}") from exc

    result = body.get("result")
    if result is None:
        raise QmdBridgeError(f"qmd tools/call '{name}' malformed response: {body!r}")
    if result.get("isError"):
        raise QmdBridgeError(f"qmd tool '{name}' reported error: {result!r}")

    if "structuredContent" in result:
        structured: dict[str, Any] = result["structuredContent"]
        return structured
    # Fall back to the text content block (e.g. doc_read returns JSON-as-text,
    # no structuredContent field) — parse it if it looks like JSON, else wrap it.
    text = "".join(
        block.get("text", "") for block in result.get("content", []) if block.get("type") == "text"
    )
    try:
        parsed: dict[str, Any] = json.loads(text)
        return parsed
    except json.JSONDecodeError:
        return {"text": text}


async def retrieve(query: str, *, collection: str = "aii-books", limit: int = 5) -> dict[str, Any]:
    """Hybrid search over the qmd collection (BM25 + vector once embedded + rerank).

    Args:
        query: Free-text search query.
        collection: qmd collection name (default: the Stratum book corpus).
        limit: Max results.

    Returns:
        {"results": [{"docid", "file", "title", "score", "snippet", "line"}, ...]}
        `score` is a 0-1 retrieval-relevance score (RRF-derived), not a
        similarity/duplicate metric — see dedup_prefilter for that usage.

    Raises:
        QmdBridgeError: qmd call failed.
    """
    return await _mcp_call_tool("query", {"query": query, "collection": collection, "limit": limit})


async def deep_read(file_or_docid: str, address: str) -> dict[str, Any]:
    """Read a specific address (e.g. 'line:45-120') from one document.

    Args:
        file_or_docid: Collection-relative path (e.g. 'aii-books/经济学/x.md')
            or a qmd docid ('#abc123') from a prior retrieve() result.
        address: Address string from doc_toc/doc_grep/retrieve (e.g. 'line:45-120').

    Returns:
        {"file": ..., "sections": [{"address", "text", "num_tokens"}, ...]}

    Raises:
        QmdBridgeError: qmd call failed.
    """
    return await _mcp_call_tool("doc_read", {"file": file_or_docid, "addresses": [address]})


async def dedup_prefilter(
    ku_text: str, *, collection: str = "aii-books", threshold: float = 0.3
) -> list[dict[str, Any]]:
    """Retrieval-relevance prefilter for a KU candidate — NOT a duplicate detector.

    MINERU-AII-INTEGRATION-SPEC-001 §3.3/§4.2: qmd has no dedicated dedup tool,
    so this composes retrieve() and keeps hits whose retrieval-relevance score
    is >= threshold. A hit above threshold means "the collection has content
    the search judged topically close to ku_text" — it is NOT a claim that the
    matched passage is a duplicate/near-duplicate of ku_text. The full identity
    judgment (is this actually the same claim?) stays in AII's translate ->
    identity-judgment chain per spec's "宁冗余不误删" principle; this prefilter
    only decides whether that expensive chain is worth running at all.

    [PENDING-TRACK-A-2W]: threshold=0.3 is spec §4.2's frozen starting value.
    Re-review after ~2 weeks of Track A traffic isn't about dedup-similarity
    calibration (there's no such axis here) — it's about whether 0.3 on this
    retrieval-relevance scale actually separates "worth a full identity check"
    from "not worth it" at a reasonable hit rate. Revisit against real
    precision/recall on the prefilter -> identity-chain funnel once there's
    traffic to look at.

    Args:
        ku_text: Candidate KU's natural-language text (used verbatim as the query).
        collection: qmd collection to search.
        threshold: Minimum retrieval-relevance score (0-1) to keep a hit.

    Returns:
        List of hits (same shape as retrieve()'s "results") with score >= threshold.
        Empty list means "nothing in the collection scored as topically close" —
        the caller should skip the full identity-judgment chain per §4.2.

    Raises:
        QmdBridgeError: qmd call failed.
    """
    hits = await retrieve(ku_text, collection=collection, limit=20)
    return [h for h in hits.get("results", []) if h.get("score", 0.0) >= threshold]
