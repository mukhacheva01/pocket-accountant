from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from shared.db.enums import EntityType, TaxRegime


@dataclass
class ProfileContext:
    entity_type: EntityType
    tax_regime: TaxRegime
    has_employees: bool
    marketplaces_enabled: bool
    region: str
    industry: Optional[str] = None
    reminder_offsets: List[int] = field(default_factory=lambda: [3, 1])


def _matches_option(value: str, allowed_values: Iterable[str]) -> bool:
    allowed_list = list(allowed_values)
    return not allowed_list or value in allowed_list


def template_matches_profile(template, profile: ProfileContext) -> bool:
    if not _matches_option(profile.entity_type.value, template.applies_to_entity_types):
        return False
    if not _matches_option(profile.tax_regime.value, template.applies_to_tax_regimes):
        return False
    if template.applies_if_has_employees is not None and template.applies_if_has_employees != profile.has_employees:
        return False
    if template.applies_if_marketplaces is not None and template.applies_if_marketplaces != profile.marketplaces_enabled:
        return False
    if template.applies_to_regions and profile.region not in template.applies_to_regions:
        return False
    return True
