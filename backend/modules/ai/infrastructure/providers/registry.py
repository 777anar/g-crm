"""Resolves a provider name to its AIProvider implementation.

Phase 21 (Real AI Provider Integration): `anthropic` resolves to a real
`AnthropicProvider` calling the live Claude API; `openai`/`gemini`/`ollama`/
`azure_openai` remain mapped to the mock, named here so every other layer
(schemas, tests, the frontend provider filter) already has a stable
vocabulary to validate against/display once one of those is genuinely
integrated later, exactly as this module's original docstring described.
Registering another real provider is a one-line change to `_PROVIDERS`
below, with no change to any use case or to core -- this mirrors the exact
pattern Communication's channel provider registry already established.
"""
from typing import Dict, Optional

from core.config import settings
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
from modules.ai.infrastructure.providers.anthropic_provider import AnthropicProvider
from modules.ai.infrastructure.providers.base import AIProvider
from modules.ai.infrastructure.providers.mock_provider import MockAIProvider

_MOCK_PROVIDER = MockAIProvider()
_ANTHROPIC_PROVIDER = AnthropicProvider()

_PROVIDERS: Dict[str, AIProvider] = {
    AI_PROVIDER_MOCK: _MOCK_PROVIDER,
    AI_PROVIDER_OPENAI: _MOCK_PROVIDER,
    AI_PROVIDER_ANTHROPIC: _ANTHROPIC_PROVIDER,
    AI_PROVIDER_GEMINI: _MOCK_PROVIDER,
    AI_PROVIDER_OLLAMA: _MOCK_PROVIDER,
    AI_PROVIDER_AZURE_OPENAI: _MOCK_PROVIDER,
}


def get_provider(provider_name: Optional[str] = None) -> AIProvider:
    # `settings.ai_default_provider` lets ops flip every company's default
    # (mock <-> anthropic) via one environment variable -- e.g. an instant
    # rollback to mock during a cost incident -- without redeploying any
    # code that calls get_provider() without an explicit provider_name.
    name = provider_name or settings.ai_default_provider or DEFAULT_AI_PROVIDER
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise UnknownAIProviderError(f"No AI provider registered for '{name}'")
    return provider
