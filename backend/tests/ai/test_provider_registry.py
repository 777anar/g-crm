"""Tests for the AIProvider registry -- the seam Phase 21's real Anthropic
integration plugged into, and the seam future OpenAI/Gemini/Ollama/Azure
OpenAI integrations still will."""
import pytest

from modules.ai.domain.exceptions import UnknownAIProviderError
from modules.ai.domain.value_objects import (
    AI_PROVIDER_ANTHROPIC,
    AI_PROVIDER_AZURE_OPENAI,
    AI_PROVIDER_GEMINI,
    AI_PROVIDER_MOCK,
    AI_PROVIDER_OLLAMA,
    AI_PROVIDER_OPENAI,
)
from modules.ai.infrastructure.providers.anthropic_provider import AnthropicProvider
from modules.ai.infrastructure.providers.base import AIProvider
from modules.ai.infrastructure.providers.mock_provider import MockAIProvider
from modules.ai.infrastructure.providers.registry import get_provider


def test_default_provider_is_mock():
    provider = get_provider()
    assert isinstance(provider, MockAIProvider)
    assert provider.name == "mock"


def test_get_provider_by_explicit_name():
    provider = get_provider(AI_PROVIDER_MOCK)
    assert isinstance(provider, MockAIProvider)


def test_anthropic_provider_name_resolves_to_the_real_provider():
    """Phase 21: 'anthropic' is no longer a placeholder slot -- it resolves
    to a real AnthropicProvider instance, calling the live Claude API when
    configured (see test_anthropic_provider.py)."""
    provider = get_provider(AI_PROVIDER_ANTHROPIC)
    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "anthropic"


@pytest.mark.parametrize(
    "provider_name", [AI_PROVIDER_OPENAI, AI_PROVIDER_GEMINI, AI_PROVIDER_OLLAMA, AI_PROVIDER_AZURE_OPENAI]
)
def test_still_unimplemented_real_providers_resolve_to_mock(provider_name):
    """Every other named future provider slot exists and resolves today --
    to the mock -- so callers don't need special-case handling once one of
    these is registered too; only registry.py's internal mapping changes
    then, exactly as it just did for 'anthropic'."""
    provider = get_provider(provider_name)
    assert isinstance(provider, MockAIProvider)


def test_unknown_provider_name_raises():
    with pytest.raises(UnknownAIProviderError):
        get_provider("not-a-real-provider")


def test_mock_provider_implements_the_ai_provider_interface():
    provider = MockAIProvider()
    assert isinstance(provider, AIProvider)
    assert provider.model == "mock-heuristic-v1"


def test_mock_provider_analysis_methods_return_confidence_between_0_and_1():
    provider = MockAIProvider()
    result = provider.analyze_lead(prompt="x", context={"lead": {"id": "1", "full_name": "A"}, "other_leads": [], "customers": []})
    assert 0.0 <= result.confidence <= 1.0
