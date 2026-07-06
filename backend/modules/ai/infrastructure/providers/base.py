"""The provider seam every real AI integration (OpenAI, Anthropic, Google
Gemini, Ollama/local LLMs, Azure OpenAI) will implement later.

No use case (see application/use_cases/analysis_use_cases.py) ever imports a
concrete provider directly -- it always resolves one through
`registry.get_provider()`. Plugging in a real integration is therefore a
change to this module's infrastructure layer only (implement this
interface, register it in registry.py): no change to any use case, any
other module, or the core. This mirrors the exact pattern already
established by Communication's ChannelProvider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AIAnalysisResult:
    """What every AIProvider method returns: the structured analysis payload
    plus the provider's own confidence in it (0.0-1.0). Execution time is
    measured by the calling use case (wall-clock around the provider call),
    not reported by the provider itself, so it stays comparable across
    every provider without each one needing to implement timing."""

    data: Dict[str, Any]
    confidence: float


class AIProvider(ABC):
    #: Short machine name, e.g. "mock" -- stored on every AIRecommendation
    #: this provider produces.
    name: str
    #: The underlying model identifier, e.g. "mock-heuristic-v1" for the
    #: mock, or "gpt-4o"/"claude-sonnet-5"/"gemini-1.5-pro" for a real
    #: provider later -- also stored on every AIRecommendation.
    model: str

    @abstractmethod
    def analyze_lead(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """CRM Intelligence: score, win probability, priority, next best
        action, follow-up, duplicate/similar detection, missing-info
        detection, and a plain-language quality explanation for one Lead."""
        raise NotImplementedError

    @abstractmethod
    def analyze_conversation(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """Communication Intelligence: language/intent/sentiment/urgency,
        a summary, extracted contact details, and a CRM-linking suggestion
        for one Conversation."""
        raise NotImplementedError

    @abstractmethod
    def analyze_quote(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """Sales Intelligence: product/cross-sell/upsell recommendations,
        a discount suggestion, margin-risk and price-anomaly detection, and
        a delivery-complexity estimate for one Quote."""
        raise NotImplementedError

    @abstractmethod
    def suggest_tasks(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """Task Intelligence: new task/reminder suggestions, an assignee
        suggestion based on current workload, task-priority suggestions,
        and overdue-risk detection, company-wide."""
        raise NotImplementedError
