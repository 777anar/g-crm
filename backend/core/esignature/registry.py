from typing import Dict, Optional, Type

from core.config import settings
from core.esignature.providers.base import ESignatureProvider
from core.esignature.providers.dropbox_sign_provider import DropboxSignProvider
from core.esignature.providers.mock_provider import MockESignatureProvider

_PROVIDERS: Dict[str, Type[ESignatureProvider]] = {
    "mock": MockESignatureProvider,
    "dropbox_sign": DropboxSignProvider,
}

_instances: Dict[str, ESignatureProvider] = {}


def get_esignature_provider(name: Optional[str] = None) -> ESignatureProvider:
    resolved_name = name or settings.esignature_default_provider
    provider_cls = _PROVIDERS.get(resolved_name)
    if provider_cls is None:
        from core.api.errors import ValidationAPIError

        raise ValidationAPIError(f"Unknown e-signature provider '{resolved_name}'")
    if resolved_name not in _instances:
        _instances[resolved_name] = provider_cls()
    return _instances[resolved_name]
