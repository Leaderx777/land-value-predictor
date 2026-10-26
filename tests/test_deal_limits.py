from dataclasses import replace

import pytest

from deal_finance import Deal
from deal_limits import Limits


def example():
    return Deal(20000, 1000, 0, 120, 0, 35000, 6)


def test_cash_limit_does_not_become_price_ceiling():
    deal = example()
    checks = Limits(max_upfront_cash=5000, max_total_cash=5000).check(
        deal, deal.analyze(), state="FL", property_type="House")
    assert all(r['passed'] for r in checks)
    checks = Limits(max_purchase_price=5000).check(deal, deal.analyze(), state="FL", property_type="House")
    assert not next(r for r in checks if r['rule'] == 'Purchase price')['passed']


def test_zero_cap_is_enforced_and_disabled_limits_are_absent():
    deal = example()
    checks = Limits(max_upfront_cash=0, min_roi_pct=None).check(deal, deal.analyze(), state="IL", property_type="Land")
    assert len(checks) == 1 and not checks[0]['passed']
    assert Limits(min_roi_pct=None).check(deal, deal.analyze(), state="IL", property_type="Land") == []


def test_location_type_financing_and_holding_constraints():
    deal = example()
    limits = Limits(states=("FL",), property_types=("House",), financing="Cash purchase", max_holding_months=3)
    checks = limits.check(deal, deal.analyze(), state="IL", property_type="Land")
    assert {'State', 'Property type', 'Purchase financing', 'Holding months'} <= {r['rule'] for r in checks if not r['passed']}


def test_empty_enabled_geography_matches_nothing():
    deal = example()
    assert not next(r for r in Limits(states=()).check(deal, deal.analyze(), state="FL", property_type="House") if r['rule'] == 'State')['passed']


def test_balloons_are_captured_in_peak_cash_separately_from_regular_payment():
    deal = replace(example(), purchase_balloon=3)
    checks = Limits(max_total_cash=5000, max_monthly_outflow=500).check(deal, deal.analyze(), state="FL", property_type="House")
    assert not next(r for r in checks if r['rule'] == 'Peak deal cash')['passed']
    assert next(r for r in checks if r['rule'] == 'Regular monthly payment + holding')['passed']


def test_upfront_costs_remain_required_even_if_same_month_resale_offsets_them():
    deal = replace(example(), resale_month=0, buying_costs=5000)
    assert not next(r for r in Limits(max_total_cash=5000).check(deal, deal.analyze(), state="IL", property_type="Land") if r['rule'] == 'Peak deal cash')['passed']


@pytest.mark.parametrize('kwargs', [dict(max_purchase_price=-1), dict(states=("XX",)), dict(max_holding_months=1.5)])
def test_invalid_limit_settings_rejected(kwargs):
    with pytest.raises(ValueError):
        Limits(**kwargs)
