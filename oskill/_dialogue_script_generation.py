"""oskill.dialogue_script_generation — generate multi-speaker dialogue script."""

from __future__ import annotations

from typing import Any


def dialogue_script_generation(
    *,
    content: str,
    speakers: list[str] | None = None,
    llm_caller: Any = None,
    max_turns: int = 12,
) -> list[dict[str, str]]:
    """Generate a dialogue script (list of {speaker, text}) from content."""
    speakers = speakers or ["Host", "Guest"]
    if not content or not content.strip():
        return []
    turns: list[dict[str, str]] = []
    if llm_caller is not None:
        try:
            resp = llm_caller(messages=[{"role": "user", "content": f"Create a {max_turns}-turn dialogue between {speakers} about:\n{content}"}], max_tokens=2048)
            text = resp.get("content", "") if isinstance(resp, dict) else str(resp)
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # parse "Speaker: text"
                if ":" in line:
                    sp, txt = line.split(":", 1)
                    sp = sp.strip()
                    if sp not in speakers:
                        sp = speakers[len(turns) % len(speakers)]
                    turns.append({"speaker": sp, "text": txt.strip()})
                if len(turns) >= max_turns:
                    break
        except Exception:
            pass
    if not turns:
        # heuristic fallback: chunk content into turns
        words = content.split()
        chunk_size = max(1, len(words) // max(1, max_turns))
        for i in range(0, len(words), chunk_size):
            if len(turns) >= max_turns:
                break
            turns.append({"speaker": speakers[len(turns) % len(speakers)], "text": " ".join(words[i:i+chunk_size])})
    return turns[:max_turns]
