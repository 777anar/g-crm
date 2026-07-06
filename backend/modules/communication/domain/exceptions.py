class CommunicationDomainError(Exception):
    pass


class ChannelInactiveError(CommunicationDomainError):
    """Raised when trying to send a message through a deactivated channel."""


class InvalidConversationStatusError(CommunicationDomainError):
    """Raised when a conversation status update targets a value outside
    VALID_CONVERSATION_STATUSES."""
