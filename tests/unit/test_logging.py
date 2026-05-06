"""Tests for shared.logging."""

from shared.logging import configure_logging


def test_configure_logging_info():
    configure_logging("INFO")


def test_configure_logging_debug():
    configure_logging("DEBUG")
