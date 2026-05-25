"""Deterministic in-memory LLM client.

Used by:
    * unit tests that exercise domain code without network
    * local dev when an API key is not configured
    * CI runs (we never hit a real provider in CI)

Responses are scripted ahead of time. Calling with an exhausted script raises,
forcing tests to be explicit about every expected call.
"""

from neetai_llm_fake.client import FakeLLMClient, ScriptedResponse

__all__ = ["FakeLLMClient", "ScriptedResponse"]
