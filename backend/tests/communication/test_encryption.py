"""Credential encryption at rest (infrastructure/security/encryption.py)."""
import pytest

from modules.communication.infrastructure.security.encryption import (
    CredentialDecryptionError,
    decrypt_text,
    encrypt_text,
)


def test_encrypt_then_decrypt_round_trips():
    plaintext = "super-secret-access-token-12345"
    ciphertext = encrypt_text(plaintext)
    assert ciphertext != plaintext
    assert decrypt_text(ciphertext) == plaintext


def test_ciphertext_is_not_plaintext_substring():
    plaintext = "EAAG_meta_access_token_value"
    ciphertext = encrypt_text(plaintext)
    assert plaintext not in ciphertext


def test_decrypting_garbage_raises_decryption_error():
    with pytest.raises(CredentialDecryptionError):
        decrypt_text("not-a-valid-fernet-token")
