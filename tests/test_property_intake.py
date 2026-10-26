from dataclasses import asdict

import pandas as pd
import pytest

from deal_finance import Deal
from deal_limits import Limits
from property_intake import ListingError, fetch_batch, normalize_rentcast, screen_listings, worksheet

NOW = pd.Timestamp('2026-10-26', tz='UTC')


def records():
    return [dict(id='a', formattedAddress='Fixture property, FL', state='FL', propertyType='Single Family',
                 price=20000, status='Active', lastSeenDate='2026-10-25')]


def frame():
    return normalize_rentcast(records())


class Response:
    status_code = 200
    def __init__(self, data, total):
        self.data = data
        self.headers = {'X-Total-Count': str(total)}
    def json(self):
        return self.data


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append(kwargs['params'])
        return next(self.responses)


def test_listing_does_not_invent_roi_financing_or_sale_value():
    result = screen_listings(frame(), Limits(max_upfront_cash=5000), now=NOW)
    assert result.iloc[0].screen_status == 'NEEDS_UNDERWRITING'
    assert pd.isna(result.iloc[0].net_roi_pct)
    sheet = worksheet(frame())
    assert sheet.iloc[0].purchase_price == 20000
    assert pd.isna(sheet.iloc[0].purchase_down)
    assert pd.isna(sheet.iloc[0].sale_price)


def test_stale_and_inactive_properties_cannot_pass():
    rows = frame()
    rows.loc[0, 'last_seen_date'] = '2020-01-01'
    assert screen_listings(rows, Limits(), now=NOW).iloc[0].screen_status == 'NEEDS_LISTING_FACTS'
    rows.loc[0, 'status'] = 'Inactive'
    assert screen_listings(rows, Limits(), now=NOW).iloc[0].screen_status == 'NOT_ACTIVE'


def test_bounded_paging_resumes_and_cash_does_not_limit_asking_price():
    session = Session([Response(records(), 2), Response([dict(records()[0], id='b')], 2)])
    _, first = fetch_batch('fixture', ['FL', 'IL'], page_size=1, session=session)
    assert first['cursor'] == {'state_index': 0, 'offset': 1}
    _, second = fetch_batch('fixture', ['FL', 'IL'], page_size=1, cursor=first['cursor'], session=session)
    assert second['cursor'] == {'state_index': 1, 'offset': 0}
    assert not second['scan_finished']
    assert len(session.calls) == 2
    assert 'price' not in session.calls[0]
    assert session.calls[1]['offset'] == 1


def test_failure_keeps_successful_rows_and_retry_cursor_without_secret():
    bad = Response([], 0)
    bad.status_code = 429
    session = Session([Response(records(), 1), bad])
    rows, report = fetch_batch('secret-fixture', ['FL', 'IL'], request_budget=2, session=session)
    assert len(rows) == 1
    assert report['cursor'] == {'state_index': 1, 'offset': 0}
    assert 'secret-fixture' not in str(report)
    assert report['errors']


def complete():
    rows = worksheet(frame())
    deal = Deal(20000, 1000, 0, 120, 0, 35000, 6, 100, 100, .05, 100, 50)
    for key, value in asdict(deal).items():
        rows[key] = value
    for key in ['resale_evidence_source', 'costs_evidence_source', 'financing_evidence_source']:
        rows[key] = 'https://example.org/fixture-only'
    return rows


def test_completed_scenario_passes_only_entered_rules_and_rechecks_cost_changes():
    rows = complete()
    limits = Limits(max_upfront_cash=5000)
    assert screen_listings(rows, limits, now=NOW).iloc[0].screen_status == 'PASSES_ENTERED_LIMITS'
    rows['improvements'] = 15000
    assert screen_listings(rows, limits, now=NOW).iloc[0].screen_status == 'FAILS_ENTERED_LIMITS'


def test_unverified_financing_and_missing_zero_cost_do_not_silently_pass():
    rows = complete()
    rows['financing_evidence_source'] = ''
    assert screen_listings(rows, Limits(), now=NOW).iloc[0].screen_status == 'NEEDS_UNDERWRITING'
    rows = complete()
    rows['buying_costs'] = None
    assert screen_listings(rows, Limits(), now=NOW).iloc[0].screen_status == 'NEEDS_UNDERWRITING'


def test_fractional_months_and_invalid_schema_rejected():
    rows = complete()
    rows['resale_month'] = 1.5
    assert screen_listings(rows, Limits(), now=NOW).iloc[0].screen_status == 'INVALID_UNDERWRITING'
    with pytest.raises(ListingError):
        screen_listings(pd.DataFrame({'price': [1]}), Limits())


def test_zero_price_cap_and_property_type_limit_enforced():
    rows = frame()
    assert screen_listings(rows, Limits(max_purchase_price=0), now=NOW).iloc[0].screen_status == 'OUTSIDE_LISTING_LIMITS'
    assert screen_listings(rows, Limits(property_types=('Land',)), now=NOW).iloc[0].screen_status == 'OUTSIDE_LISTING_LIMITS'
