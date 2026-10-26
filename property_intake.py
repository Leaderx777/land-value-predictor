"""Listing intake and underwriting without inventing resale values or financing."""
from dataclasses import fields
from datetime import datetime, timezone
import math
from urllib.parse import urlparse

import pandas as pd
import requests

from deal_finance import Deal
from deal_limits import Limits, PROPERTY_TYPES, STATES

RENTCAST_URL = 'https://api.rentcast.io/v1/listings/sale'
TYPE_MAP = {'Single Family': 'House', 'Condo': 'Condo / townhouse', 'Townhouse': 'Condo / townhouse',
            'Manufactured': 'Manufactured / mobile home', 'Multi-Family': 'Multifamily',
            'Apartment': 'Multifamily', 'Land': 'Land'}
BASE_COLUMNS = ['listing_id', 'address', 'state', 'property_type', 'asking_price', 'status', 'last_seen_date', 'source']
UNDERWRITING_COLUMNS = [f.name for f in fields(Deal)] + ['resale_evidence_source', 'costs_evidence_source', 'financing_evidence_source']


class ListingError(ValueError):
    pass


def normalize_rentcast(records):
    now = datetime.now(timezone.utc).isoformat()
    return pd.DataFrame([dict(listing_id=str(r.get('id') or ''), address=r.get('formattedAddress'),
        state=r.get('state'), property_type=TYPE_MAP.get(r.get('propertyType'), 'Other real estate'),
        asking_price=r.get('price'), status=r.get('status'), last_seen_date=r.get('lastSeenDate'),
        source='RentCast', retrieved_at=now, provider_property_type=r.get('propertyType')) for r in records],
        columns=BASE_COLUMNS + ['retrieved_at', 'provider_property_type'])


def fetch_batch(api_key, states, *, page_size=100, request_budget=1, cursor=None, session=None, max_price=None):
    """Bounded, resumable state scans. A batch is never a complete national search."""
    if not api_key or not api_key.strip():
        raise ListingError('Enter a RentCast API key or use CSV intake')
    if not states or not set(states).issubset(STATES):
        raise ListingError('Select valid states')
    if not 1 <= page_size <= 500 or not 1 <= request_budget <= 51:
        raise ListingError('Use 1–500 rows/request and 1–51 requests/batch')
    if max_price is not None and (not math.isfinite(max_price) or max_price < 0):
        raise ListingError('Invalid price limit')
    cursor = dict(cursor or {'state_index': 0, 'offset': 0})
    if not 0 <= cursor['state_index'] <= len(states) or cursor['offset'] < 0:
        raise ListingError('Invalid scan cursor')
    session = session or requests.Session()
    records, pages, errors = [], [], []
    for _ in range(request_budget):
        index = cursor['state_index']
        if index >= len(states):
            break
        state, offset = states[index], cursor['offset']
        params = dict(state=state, status='Active', limit=page_size, offset=offset, includeTotalCount='true')
        if max_price is not None:
            params['price'] = f'0:{max_price:g}'
        try:
            response = session.get(RENTCAST_URL, params=params, headers={'X-Api-Key': api_key}, timeout=30)
            if response.status_code != 200:
                # Never return response bodies, which can contain request/account information.
                raise ListingError(f'Listing provider returned HTTP {response.status_code}; check access/quota')
            payload = response.json()
            if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                raise ListingError('Unexpected provider response')
            total = response.headers.get('X-Total-Count')
            total = int(total) if total is not None else None
        except (requests.RequestException, ValueError) as exc:
            errors.append(dict(state=state, offset=offset, error=str(exc) if isinstance(exc, ListingError) else 'Provider request failed; retry this batch'))
            break
        records.extend(payload)
        pages.append(dict(state=state, offset=offset, rows=len(payload), provider_total=total))
        if len(payload) < page_size or (total is not None and offset + len(payload) >= total):
            cursor = {'state_index': index + 1, 'offset': 0}
        else:
            cursor = {'state_index': index, 'offset': offset + len(payload)}
    frame = normalize_rentcast(records)
    frame = frame.drop_duplicates('listing_id') if not frame.empty else frame
    return frame, {'cursor': cursor, 'requests_made': len(pages) + len(errors), 'pages': pages, 'errors': errors,
                   'scan_finished': cursor['state_index'] >= len(states),
                   'note': 'Provider results only; availability and market value require independent confirmation'}


def _number(row, name):
    value = pd.to_numeric(row.get(name), errors='coerce')
    return float(value) if pd.notna(value) and math.isfinite(float(value)) else None


def _source(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)


def screen_listings(frame, limits: Limits, *, now=None, max_age_days=7):
    if set(BASE_COLUMNS) - set(frame.columns):
        raise ListingError(f'Missing listing columns: {sorted(set(BASE_COLUMNS) - set(frame.columns))}')
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    now = now.tz_localize('UTC') if now.tz is None else now.tz_convert('UTC')
    outputs = []
    for _, row in frame.iterrows():
        out = row.to_dict()
        out.update(screen_status='NEEDS_UNDERWRITING', reasons='', net_profit=None, net_roi_pct=None)
        issues = []
        if str(row.get('status', '')).strip().lower() != 'active':
            out.update(screen_status='NOT_ACTIVE', reasons='Provider/source does not report active')
            outputs.append(out)
            continue
        if not str(row.get('listing_id', '')).strip() or pd.isna(row.get('listing_id')):
            issues.append('missing listing ID')
        if row.get('state') not in STATES or row.get('property_type') not in PROPERTY_TYPES:
            issues.append('unknown state/property type')
        price = _number(row, 'asking_price')
        if price is None or price <= 0:
            issues.append('missing/invalid asking price')
        seen = pd.to_datetime(row.get('last_seen_date'), utc=True, errors='coerce')
        if pd.isna(seen) or seen > now or now - seen > pd.Timedelta(days=max_age_days):
            issues.append('availability needs rechecking')
        if not isinstance(row.get('source'), str) or not row['source'].strip():
            issues.append('missing listing source')
        failures = []
        if price is not None and limits.max_purchase_price is not None and price > limits.max_purchase_price:
            failures.append('asking price above price ceiling')
        if limits.states is not None and row.get('state') not in limits.states:
            failures.append('state excluded')
        if limits.property_types is not None and row.get('property_type') not in limits.property_types:
            failures.append('property type excluded')
        if failures:
            out.update(screen_status='OUTSIDE_LISTING_LIMITS', reasons='; '.join(failures))
            outputs.append(out)
            continue
        if issues:
            out.update(screen_status='NEEDS_LISTING_FACTS', reasons='; '.join(issues))
            outputs.append(out)
            continue
        inputs = {f.name: _number(row, f.name) for f in fields(Deal)}
        missing = [k for k, v in inputs.items() if v is None]
        evidence = [k for k in ['resale_evidence_source', 'costs_evidence_source'] if not _source(row.get(k))]
        if inputs.get('purchase_price') is not None and inputs.get('purchase_down') is not None and inputs['purchase_down'] < inputs['purchase_price']:
            if not _source(row.get('financing_evidence_source')):
                evidence.append('financing_evidence_source')
        if missing or evidence:
            out['reasons'] = 'Needs explicit inputs/evidence: ' + ', '.join(missing + evidence)
            outputs.append(out)
            continue
        try:
            for key in ['purchase_term', 'purchase_balloon', 'resale_month']:
                if int(inputs[key]) != inputs[key]:
                    raise ValueError(f'{key} must be a whole month')
                inputs[key] = int(inputs[key])
            deal = Deal(**inputs)
            result = deal.analyze()
            checks = limits.check(deal, result, state=row['state'], property_type=row['property_type'])
            failed = [c['rule'] for c in checks if not c['passed']]
            out.update(screen_status='FAILS_ENTERED_LIMITS' if failed else ('PASSES_ENTERED_LIMITS' if checks else 'NO_LIMITS_ENABLED'),
                       reasons='; '.join(failed) if failed else 'Scenario inputs only; evidence content and due diligence are not automatically verified',
                       net_profit=result['profit'], net_roi_pct=result['project_roi_pct'])
        except ValueError as exc:
            out.update(screen_status='INVALID_UNDERWRITING', reasons=str(exc))
        outputs.append(out)
    return pd.DataFrame(outputs)


def worksheet(frame):
    result = frame.copy()
    for column in UNDERWRITING_COLUMNS:
        if column not in result:
            result[column] = pd.NA
    # Asking price is a proposed purchase assumption; all other financials stay blank.
    price = pd.to_numeric(result['purchase_price'], errors='coerce')
    result['purchase_price'] = price.where(price.notna(), pd.to_numeric(result['asking_price'], errors='coerce'))
    return result
