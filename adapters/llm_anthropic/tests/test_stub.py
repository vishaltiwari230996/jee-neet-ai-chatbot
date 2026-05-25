import pytest

from neetai_llm_anthropic import AnthropicClient, AnthropicConfig
from neetai_ports import (
    CompletionRequest,
    LLMClient,
    LLMMessage,
    LLMRole,
    ModelTier,
)


def test_satisfies_llm_client_protocol() -> None:
    client = AnthropicClient(AnthropicConfig(api_key="x"))
    assert isinstance(client, LLMClient)


async def test_complete_raises_until_implemented() -> None:
    client = AnthropicClient(AnthropicConfig(api_key="x"))
    with pytest.raises(NotImplementedError):
        await client.complete(
            CompletionRequest(
                tier=ModelTier.CHEAP,
                messages=[LLMMessage(role=LLMRole.USER, content="hi")],
            ),
        )
