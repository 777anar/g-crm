"""Encryption at rest for third-party integration credentials (access
tokens, SMTP/IMAP passwords, webhook secrets). Nothing in this module ever
stores a credential value in plaintext -- ChannelCredential.encrypted_config
and .webhook_secret_encrypted are always the output of `encrypt_text`, and
are only ever decrypted transiently inside a provider's constructor for the
duration of one API call, never returned to the frontend (see
presentation/schemas/channel_credential.py's masking).

`settings.channel_credentials_encryption_key` is an arbitrary operator-
supplied string, not a raw Fernet key -- stretching it via SHA-256 means any
string works as a valid 32-byte key, so operators don't have to hand-
generate the base64 Fernet format themselves.
"""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


class CredentialDecryptionError(Exception):
    """Raised when stored ciphertext can't be decrypted with the current
    key -- e.g. CHANNEL_CREDENTIALS_ENCRYPTION_KEY was rotated without
    re-encrypting existing rows."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.channel_credentials_encryption_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_text(plaintext: str) -> str:
    if plaintext is None:
        return plaintext
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_text(ciphertext: str) -> str:
    if ciphertext is None:
        return ciphertext
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialDecryptionError("Stored credential could not be decrypted") from exc
