"""Tests for shared.secrets.SecretBox."""

import pytest
from cryptography.fernet import Fernet

from shared.secrets import SecretBox


@pytest.fixture()
def fernet_key() -> str:
    return Fernet.generate_key().decode()


def test_encrypt_decrypt_roundtrip(fernet_key):
    box = SecretBox(fernet_key)
    ct = box.encrypt("hello")
    assert ct.startswith(SecretBox.PREFIX)
    assert box.decrypt(ct) == "hello"


def test_encrypt_empty_string(fernet_key):
    box = SecretBox(fernet_key)
    assert box.encrypt("") == ""


def test_decrypt_empty_string(fernet_key):
    box = SecretBox(fernet_key)
    assert box.decrypt("") == ""


def test_encrypt_already_encrypted(fernet_key):
    box = SecretBox(fernet_key)
    ct = box.encrypt("data")
    assert box.encrypt(ct) == ct


def test_decrypt_plaintext_passthrough(fernet_key):
    box = SecretBox(fernet_key)
    assert box.decrypt("not_encrypted") == "not_encrypted"


def test_enabled_property():
    box = SecretBox("", allow_insecure_fallback=True)
    assert box.enabled is False
    key = Fernet.generate_key().decode()
    box2 = SecretBox(key)
    assert box2.enabled is True


def test_can_store_plaintext():
    box = SecretBox("", allow_insecure_fallback=True)
    assert box.can_store_plaintext is True
    box2 = SecretBox("", allow_insecure_fallback=False)
    assert box2.can_store_plaintext is False


def test_insecure_fallback_passthrough():
    box = SecretBox("", allow_insecure_fallback=True)
    assert box.encrypt("data") == "data"


def test_insecure_fallback_disabled_raises():
    box = SecretBox("", allow_insecure_fallback=False)
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY is required"):
        box.encrypt("data")


def test_decrypt_without_key_raises():
    box = SecretBox("")
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY is required to decrypt"):
        box.decrypt("enc-v1:garbage")


def test_decrypt_wrong_key_raises():
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    box1 = SecretBox(key1)
    box2 = SecretBox(key2)
    ct = box1.encrypt("secret")
    with pytest.raises(RuntimeError, match="cannot be decrypted"):
        box2.decrypt(ct)


def test_is_encrypted():
    box = SecretBox("")
    assert box.is_encrypted("enc-v1:something") is True
    assert box.is_encrypted("plaintext") is False
    assert box.is_encrypted("") is False
