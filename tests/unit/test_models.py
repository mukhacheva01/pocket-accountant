"""Tests for shared.db.models — ValueEnum type decorator."""

from shared.db.enums import EntityType
from shared.db.models import ValueEnum


def test_value_enum_process_bind_param():
    ve = ValueEnum(EntityType)
    assert ve.process_bind_param(EntityType.INDIVIDUAL_ENTREPRENEUR, None) == "ip"
    assert ve.process_bind_param("ip", None) == "ip"
    assert ve.process_bind_param(None, None) is None


def test_value_enum_process_result_value():
    ve = ValueEnum(EntityType)
    assert ve.process_result_value("ip", None) == EntityType.INDIVIDUAL_ENTREPRENEUR
    assert ve.process_result_value(None, None) is None


def test_value_enum_cache_ok():
    ve = ValueEnum(EntityType)
    assert ve.cache_ok is True
