"""Tests for backend.services.law_updates."""

from types import SimpleNamespace

from shared.db.enums import EntityType, LawUpdateReviewStatus, TaxRegime
from backend.services.law_updates import LawUpdateService
from backend.services.profile_matching import ProfileContext


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


def _update(
    review_status=LawUpdateReviewStatus.APPROVED,
    entity_types=None,
    tax_regimes=None,
    marketplaces=None,
):
    return SimpleNamespace(
        review_status=review_status,
        affected_entity_types=entity_types,
        affected_tax_regimes=tax_regimes,
        affected_marketplaces=marketplaces,
    )


class TestIsRelevant:
    def test_approved_no_filters(self):
        assert LawUpdateService.is_relevant(_update(), _profile())

    def test_unreviewed_not_relevant(self):
        assert not LawUpdateService.is_relevant(
            _update(review_status=LawUpdateReviewStatus.UNREVIEWED), _profile()
        )

    def test_rejected_not_relevant(self):
        assert not LawUpdateService.is_relevant(
            _update(review_status=LawUpdateReviewStatus.REJECTED), _profile()
        )

    def test_entity_type_filter_match(self):
        assert LawUpdateService.is_relevant(
            _update(entity_types=["ip"]), _profile()
        )

    def test_entity_type_filter_no_match(self):
        assert not LawUpdateService.is_relevant(
            _update(entity_types=["ooo"]), _profile()
        )

    def test_tax_regime_filter_match(self):
        assert LawUpdateService.is_relevant(
            _update(tax_regimes=["usn_income"]), _profile()
        )

    def test_tax_regime_filter_no_match(self):
        assert not LawUpdateService.is_relevant(
            _update(tax_regimes=["npd"]), _profile()
        )

    def test_marketplace_filter_match(self):
        assert LawUpdateService.is_relevant(
            _update(marketplaces=True), _profile(marketplaces_enabled=True)
        )

    def test_marketplace_filter_no_match(self):
        assert not LawUpdateService.is_relevant(
            _update(marketplaces=True), _profile(marketplaces_enabled=False)
        )

    def test_none_marketplace_matches_all(self):
        assert LawUpdateService.is_relevant(
            _update(marketplaces=None), _profile(marketplaces_enabled=False)
        )
