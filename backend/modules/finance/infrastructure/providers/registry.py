from typing import Dict, Optional, Type

from core.config import settings
from modules.finance.infrastructure.providers.base import PaymentGatewayProvider
from modules.finance.infrastructure.providers.mock_provider import MockPaymentGatewayProvider
from modules.finance.infrastructure.providers.stripe_provider import StripeProvider

_PROVIDERS: Dict[str, Type[PaymentGatewayProvider]] = {
    "mock": MockPaymentGatewayProvider,
    "stripe": StripeProvider,
}

_instances: Dict[str, PaymentGatewayProvider] = {}


def get_payment_gateway_provider(name: Optional[str] = None) -> PaymentGatewayProvider:
    resolved_name = name or settings.payment_gateway_default_provider
    provider_cls = _PROVIDERS.get(resolved_name)
    if provider_cls is None:
        from core.api.errors import ValidationAPIError

        raise ValidationAPIError(f"Unknown payment gateway provider '{resolved_name}'")
    if resolved_name not in _instances:
        _instances[resolved_name] = provider_cls()
    return _instances[resolved_name]
