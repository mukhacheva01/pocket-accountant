"""Tests for shared.db.base and session."""

from shared.db.base import Base
from shared.db.session import SessionFactory


def test_base_model_exists():
    assert Base is not None
    assert hasattr(Base, 'metadata')


def test_session_factory_exists():
    assert SessionFactory is not None
