"""Tests for backend.services.profile_matching."""

from dataclasses import dataclass

from shared.db.enums import EntityType, TaxRegime
from backend.services.profile_matching import ProfileContext, template_matches_profile


@dataclass
class FakeTemplate:
    applies_to_entity_types: list
    applies_to_tax_regimes: list
    applies_if_has_employees: bool | None
    applies_if_marketplaces: bool | None
    applies_to_regions: list


def _profile(**overrides) -> ProfileContext:
    defaults = {
        "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR,
        "tax_regime": TaxRegime.USN_INCOME,
        "has_employees": False,
        "marketplaces_enabled": False,
        "region": "Moscow",
    }
    defaults.update(overrides)
    return ProfileContext(**defaults)


class TestTemplateMatchesProfile:
    def test_exact_match(self):
        t = FakeTemplate(
            applies_to_entity_types=["ip"],
            applies_to_tax_regimes=["usn_income"],
            applies_if_has_employees=False,
            applies_if_marketplaces=False,
            applies_to_regions=["Moscow"],
        )
        assert template_matches_profile(t, _profile())

    def test_empty_lists_match_all(self):
        t = FakeTemplate(
            applies_to_entity_types=[],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
        )
        assert template_matches_profile(t, _profile())

    def test_wrong_entity_type(self):
        t = FakeTemplate(
            applies_to_entity_types=["ooo"],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
        )
        assert not template_matches_profile(t, _profile())

    def test_wrong_tax_regime(self):
        t = FakeTemplate(
            applies_to_entity_types=[],
            applies_to_tax_regimes=["npd"],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
        )
        assert not template_matches_profile(t, _profile())

    def test_wrong_region(self):
        t = FakeTemplate(
            applies_to_entity_types=[],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=["Saint Petersburg"],
        )
        assert not template_matches_profile(t, _profile())

    def test_wrong_employees(self):
        t = FakeTemplate(
            applies_to_entity_types=[],
            applies_to_tax_regimes=[],
            applies_if_has_employees=True,
            applies_if_marketplaces=None,
            applies_to_regions=[],
        )
        assert not template_matches_profile(t, _profile(has_employees=False))

    def test_wrong_marketplaces(self):
        t = FakeTemplate(
            applies_to_entity_types=[],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=True,
            applies_to_regions=[],
        )
        assert not template_matches_profile(t, _profile(marketplaces_enabled=False))

    def test_multiple_entity_types(self):
        t = FakeTemplate(
            applies_to_entity_types=["ip", "ooo"],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
        )
        assert template_matches_profile(t, _profile())
        assert template_matches_profile(t, _profile(entity_type=EntityType.LIMITED_COMPANY))
