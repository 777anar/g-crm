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
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class AIAnalysisResult:
    """What every AIProvider method returns: the structured analysis payload
    plus the provider's own confidence in it (0.0-1.0). Execution time is
    measured by the calling use case (wall-clock around the provider call),
    not reported by the provider itself, so it stays comparable across
    every provider without each one needing to implement timing.

    The four fields below are Phase 21 additions for a real provider's audit
    trail (`AIProviderCallLog`) -- `None` for `MockAIProvider`, which makes
    no real API call and has no real cost, tokens, or raw response text to
    report."""

    data: Dict[str, Any]
    confidence: float
    raw_response: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[Decimal] = None


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

    @abstractmethod
    def draft_conversation_reply(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """AI draft generation (Phase 21 follow-through): a draft reply to
        the customer's most recent message in one Conversation, in the
        conversation's own detected language -- draft-only, never sent
        automatically. The calling use case creates exactly one
        `suggested_reply` recommendation from this; a human copies the
        draft into the compose box, edits it, and sends it themselves
        through the existing send-message action."""
        raise NotImplementedError

    @abstractmethod
    def draft_quote_line_items(self, *, prompt: str, context: dict) -> AIAnalysisResult:
        """AI draft generation (Phase 21 follow-through): suggested Quote
        line-item descriptions (and a bounded waste-factor suggestion) for
        one Project's already-specified Rooms/Items -- draft-only, never
        applied to a Quote automatically. Exact quantities/prices are
        computed deterministically by the calling use case from real
        ProjectItem/PriceListEntry data; the model only supplies the
        language-shaped half (description text, a clamped waste-factor
        percentage)."""
        raise NotImplementedError
