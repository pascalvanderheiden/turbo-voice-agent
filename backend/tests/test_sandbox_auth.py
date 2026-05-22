"""Tests for sandbox authentication token handling."""

import os


def test_encrypt_decrypt_roundtrip():
    """Token survives encrypt → decrypt cycle."""
    os.environ["SANDBOX_TOKEN_KEY"] = "test-encryption-key-123"
    from app.routes.user import _decrypt_sandbox_token, _encrypt_sandbox_token

    original = "ghp_ABCdef123456789"
    encrypted = _encrypt_sandbox_token(original)
    assert encrypted != original
    decrypted = _decrypt_sandbox_token(encrypted)
    assert decrypted == original


def test_encrypt_produces_base64():
    """Encrypted token is valid base64."""
    import base64
    os.environ["SANDBOX_TOKEN_KEY"] = "test-key"
    from app.routes.user import _encrypt_sandbox_token

    encrypted = _encrypt_sandbox_token("ghp_test")
    # Should not raise
    base64.b64decode(encrypted)


def test_different_keys_produce_different_output():
    """Different encryption keys produce different ciphertext."""
    from app.routes.user import _encrypt_sandbox_token

    os.environ["SANDBOX_TOKEN_KEY"] = "key-one"
    enc1 = _encrypt_sandbox_token("same-token")
    os.environ["SANDBOX_TOKEN_KEY"] = "key-two"
    enc2 = _encrypt_sandbox_token("same-token")
    assert enc1 != enc2
