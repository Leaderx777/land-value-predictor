from dataclasses import replace
import pytest
from deal_finance import Deal, Note


def cash_deal():
    return Deal(5000, 5000, 0, 120, 0, 7500, 6, 250, 0, .06, 100, 50)


def test_cash_flip_costs_roi_and_break_even_reconcile():
    deal = cash_deal()
    r = deal.analyze()
    assert r['total_cost'] == 6100
    assert r['profit'] == 1400
    assert r['project_roi_pct'] == pytest.approx(1400 / 6100 * 100)
    assert replace(deal, sale_price=r['break_even_resale']).analyze()['profit'] == pytest.approx(0, abs=.01)


def test_financing_does_not_count_principal_twice():
    cash = cash_deal().analyze()
    financed = replace(cash_deal(), purchase_down=1000, purchase_rate=0).analyze()
    assert financed['profit'] == cash['profit']
    assert financed['total_cost'] == cash['total_cost']
    assert financed['peak_funding'] < cash['peak_funding']


def test_interest_and_payoff_match_monthly_schedule():
    deal = replace(cash_deal(), purchase_down=1000, purchase_rate=.12)
    r = deal.analyze()
    schedule = r['purchase_schedule']
    assert r['purchase_payoff_at_resale'] == schedule[5]['balance']
    assert r['profit'] == pytest.approx(cash_deal().analyze()['profit'] - r['purchase_interest_paid'], abs=.01)


def test_zero_rate_and_balloon_balance_reconcile():
    note = Note(1200, 0, 12, 3).schedule()
    assert note[-1]['balloon'] == 900
    assert sum(r['payment'] for r in note) == 1200
    assert note[-1]['balance'] == 0


def test_balloon_before_resale_requires_cash_and_no_second_payoff():
    r = replace(cash_deal(), purchase_down=1000, purchase_rate=.12, purchase_balloon=3).analyze()
    assert r['balloon_before_resale']
    assert r['purchase_payoff_at_resale'] == 0
    assert sum(row['purchase_debt'] for row in r['flows']) == pytest.approx(4000 + r['purchase_interest_paid'])


def test_same_month_resale_and_full_term_payoff():
    deal = replace(cash_deal(), purchase_down=1000, resale_month=0)
    assert deal.analyze()['purchase_payoff_at_resale'] == 4000
    assert replace(deal, resale_month=120).analyze()['purchase_payoff_at_resale'] == 0


@pytest.mark.parametrize('change', [dict(purchase_down=6000), dict(sale_price=0), dict(purchase_rate=-.1, purchase_down=1000), dict(resale_month=-1)])
def test_invalid_inputs_rejected(change):
    with pytest.raises(ValueError):
        replace(cash_deal(), **change).analyze()


def test_delay_and_lower_sale_reduce_profit():
    deal = cash_deal()
    assert replace(deal, resale_month=12).analyze()['profit'] < deal.analyze()['profit']
    assert replace(deal, sale_price=6750).analyze()['profit'] < deal.analyze()['profit']
