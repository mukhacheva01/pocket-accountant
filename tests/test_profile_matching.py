import unittest
from dataclasses import dataclass

from shared.db.enums import EntityType, TaxRegime
from backend.services.profile_matching import ProfileContext, template_matches_profile


@dataclass
class FakeTemplate:
    applies_to_entity_types: list
    applies_to_tax_regimes: list
    applies_if_has_employees: bool
    applies_if_marketplaces: bool
    applies_to_regions: list


class ProfileMatchingTests(unittest.TestCase):
    def test_template_matches_same_profile(self) -> None:
        template = FakeTemplate(
            applies_to_entity_types=["ip"],
            applies_to_tax_regimes=["usn_income"],
            applies_if_has_employees=False,
            applies_if_marketplaces=True,
            applies_to_regions=["Moscow"],
        )
        profile = ProfileContext(
            entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
            tax_regime=TaxRegime.USN_INCOME,
            has_employees=False,
            marketplaces_enabled=True,
            region="Moscow",
        )
        self.assertTrue(template_matches_profile(template, profile))

    def test_template_rejects_non_matching_region(self) -> None:
        template = FakeTemplate(
            applies_to_entity_types=["ip"],
            applies_to_tax_regimes=["usn_income"],
            applies_if_has_employees=False,
            applies_if_marketplaces=True,
            applies_to_regions=["Saint Petersburg"],
        )
        profile = ProfileContext(
            entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
            tax_regime=TaxRegime.USN_INCOME,
            has_employees=False,
            marketplaces_enabled=True,
            region="Moscow",
        )
        self.assertFalse(template_matches_profile(template, profile))


if __name__ == "__main__":
    unittest.main()
