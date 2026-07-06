"""Resolves a provider name to its AIProvider implementation.

Every provider name maps to MockAIProvider today (see its docstring for
why: no real OpenAI/Anthropic/Gemini/Ollama/Azure OpenAI integration exists
yet, by explicit design). Registering a real one later is a one-line change
to `_PROVIDERS` below -- e.g. `AI_PROVIDER_OPENAI: OpenAIProvider(...)` --
with no change to any use case or to core. This mirrors the exact pattern
already established by Communication's channel provider registry.
"""
from typing import Dict, Optional

from modules.ai.domain.exceptions import UnknownAIProviderError
from modules.ai.domain.value_objects import (
    AI_PROVIDER_ANTHROPIC,
    AI_PROVIDER_AZURE_OPENAI,
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_MOCK,
    AI_PROVIDER_OLLAMA,
    AI_PROVIDER_OPENAI,
    DEFAULT_AI_PROVIDER,
)
from modules.ai.infrastructure.providers.base import AIProvider
from modules.ai.infrastructure.providers.mock_provider import MockAIProvider

_MOCK_PROVIDER = MockAIProvider()

# Every entry resolves to the mock today. A real integration is added here,
# not by touching any use case.
_PROVIDERS: Dict[str, AIProvider] = {
    AI_PROVIDER_MOCK: _MOCK_PROVIDER,
    AI_PROVIDER_OPENAI: _MOCK_PROVIDER,
    AI_PROVIDER_ANTHROPIC: _MOCK_PROVIDER,
    AI_PROVIDER_GEMINI: _MOCK_PROVIDER,
    AI_PROVIDER_OLLAMA: _MOCK_PROVIDER,
    AI_PROVIDER_AZURE_OPENAI: _MOCK_PROVIDER,
}


def get_provider(provider_name: Optional[str] = None) -> AIProvider:
    name = provider_name or DEFAULT_AI_PROVIDER
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise UnknownAIProviderError(f"No AI provider registered for '{name}'")
    return provider
