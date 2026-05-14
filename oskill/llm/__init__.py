"""LLM integration primitives submodule."""

from oskill.llm.deterministic_call import deterministic_llm_call
from oskill.llm.prompt_fingerprint import prompt_fingerprint

__all__ = ["deterministic_llm_call", "prompt_fingerprint"]
