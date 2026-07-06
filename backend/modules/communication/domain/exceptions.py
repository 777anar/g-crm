class CommunicationDomainError(Exception):
    pass


class ChannelInactiveError(CommunicationDomainError):
    """Raised when trying to send a message through a deactivated channel."""


class InvalidConversationStatusError(CommunicationDomainError):
    """Raised when a conversation status update targets a value outside
    VALID_CONVERSATION_STATUSES."""


# ── Real integrations (Version 2.9) ─────────────────────────────────────────


class UnknownProviderError(CommunicationDomainError):
    """Raised when a provider name isn't registered (infrastructure/providers/registry.py)."""


class ProviderConfigurationError(CommunicationDomainError):
    """Raised when a channel's stored credential config is missing a field a
    provider requires to operate (e.g. no phone_number_id for WhatsApp)."""


class ProviderAuthError(CommunicationDomainError):
    """Raised when the external provider rejects our credentials (expired/
    revoked token, bad password, ...)."""


class ProviderRateLimitedError(CommunicationDomainError):
    """Raised when the external provider signals we're sending too fast."""


class ProviderRequestError(CommunicationDomainError):
    """Raised for any other non-2xx response from a real provider's API that
    isn't specifically an auth or rate-limit failure."""


class WebhookSignatureError(CommunicationDomainError):
    """Raised when an inbound webhook's signature doesn't verify against the
    channel's configured secret -- the payload is discarded, never processed
    as a trusted inbound message."""
