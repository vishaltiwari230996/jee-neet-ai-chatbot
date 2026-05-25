"""Smoke test: every port can be used with isinstance() so tests can verify
that adapters satisfy them at runtime, not just at type-check time."""

from neetai_ports import (
    AuthProvider,
    Cache,
    Clock,
    EventBus,
    LLMClient,
    VectorStore,
)


class _NotAClient:
    pass


def test_llm_client_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), LLMClient)


def test_vector_store_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), VectorStore)


def test_cache_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), Cache)


def test_event_bus_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), EventBus)


def test_clock_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), Clock)


def test_auth_provider_is_runtime_checkable() -> None:
    assert not isinstance(_NotAClient(), AuthProvider)
