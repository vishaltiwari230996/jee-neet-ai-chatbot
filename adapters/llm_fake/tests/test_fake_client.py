import pytest

from neetai_core.errors import DomainError
from neetai_llm_fake import FakeLLMClient, ScriptedResponse
from neetai_ports import (
    CompletionRequest,
    LLMClient,
    LLMMessage,
    LLMRole,
    ModelTier,
)


def _request() -> CompletionRequest:
    return CompletionRequest(
        tier=ModelTier.CHEAP,
        messages=[LLMMessage(role=LLMRole.USER, content="hi")],
    )


def test_fake_satisfies_llm_client_protocol() -> None:
    assert isinstance(FakeLLMClient(), LLMClient)


async def test_pops_scripted_responses_in_order() -> None:
    client = FakeLLMClient(
        completions=[
            ScriptedResponse(content="first"),
            ScriptedResponse(content="second"),
        ],
    )
    assert (await client.complete(_request())).content == "first"
    assert (await client.complete(_request())).content == "second"


async def test_exhausted_script_raises() -> None:
    client = FakeLLMClient()
    with pytest.raises(DomainError, match="script exhausted"):
        await client.complete(_request())


async def test_records_requests() -> None:
    client = FakeLLMClient(completions=[ScriptedResponse(content="ok")])
    req = _request()
    await client.complete(req)
    assert client.recorded_requests == [req]
