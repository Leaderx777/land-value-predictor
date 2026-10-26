"""Bounded live nationwide listing intake and user-supplied CSV underwriting."""
import json
import os

import pandas as pd
import streamlit as st

from deal_limits import Limits, STATES
from property_intake import (BASE_COLUMNS, UNDERWRITING_COLUMNS, ListingError,
                             fetch_batch, screen_listings, worksheet)

st.set_page_config(page_title='Property Search', layout='wide')
st.title('Property Search')
st.page_link('app.py', label='Edit your limits / single-deal calculator')
settings = st.session_state.get('active_limits', Limits().to_dict())
try:
    limits = Limits(**settings)
except (ValueError, TypeError):
    st.error('Invalid saved limits. Return to the calculator and reset them.')
    st.stop()
with st.expander('Current screening limits'):
    st.json(settings)
    st.caption('Disabled limits are null. Cash limits do not become a purchase-price ceiling.')
st.info('Listings start as candidates, not verified deals. ROI needs a supported resale price, costs and actual financing terms. No listing is automatically labeled a buy.')
source = st.radio('Listing source', ['Live RentCast', 'CSV upload'], horizontal=True)
if source == 'Live RentCast':
    st.caption('Supports searches across all US states. The provider covers homes, condos, manufactured homes, multifamily/apartments and some land. Retail, offices, industrial and other unsupported types can be uploaded by CSV.')
    key = st.text_input('RentCast API key', value=os.getenv('RENTCAST_API_KEY', ''), type='password')
    page_size = st.number_input('Listings per request', min_value=1, max_value=500, value=100)
    budget = st.number_input('Maximum API requests this batch', min_value=1, max_value=51, value=1)
    states = list(limits.states) if limits.states is not None else list(STATES)
    identity = json.dumps({'states': states, 'max_price': limits.max_purchase_price, 'page_size': int(page_size)}, sort_keys=True)
    if st.session_state.get('scan_identity') != identity:
        st.session_state['scan_identity'] = identity
        st.session_state['scan_cursor'] = None
        st.session_state['search_listings'] = pd.DataFrame(columns=BASE_COLUMNS)
        st.session_state['scan_report'] = None
    st.caption(f'{len(states)} states selected. Each click uses at most {int(budget)} provider request(s), which may count against your plan. A batch is a sample until all selected states/pages have been traversed.')
    left, right = st.columns(2)
    fetch = left.button('Fetch next batch', type='primary')
    if right.button('Reset scan'):
        st.session_state['scan_cursor'] = None
        st.session_state['search_listings'] = pd.DataFrame(columns=BASE_COLUMNS)
        st.session_state['scan_report'] = None
    if fetch:
        try:
            new, report = fetch_batch(key, states, page_size=int(page_size), request_budget=int(budget),
                cursor=st.session_state['scan_cursor'], max_price=limits.max_purchase_price)
            combined = pd.concat([st.session_state['search_listings'], new], ignore_index=True)
            st.session_state['search_listings'] = combined.drop_duplicates('listing_id', keep='last')
            st.session_state['scan_cursor'] = report['cursor']
            st.session_state['scan_report'] = report
        except ListingError as exc:
            st.error(str(exc))
    report = st.session_state.get('scan_report')
    if report:
        st.write('Selected provider scan finished.' if report['scan_finished'] else f"Scan incomplete. Next state position: {report['cursor']['state_index'] + 1} of {len(states)}; offset {report['cursor']['offset']}.")
        with st.expander('Last batch coverage and errors'):
            st.json(report)
        for error in report['errors']:
            st.warning(f"{error['state']}: {error['error']}. Retrieved rows remain available; retry resumes at this state/page.")
    frame = st.session_state.get('search_listings', pd.DataFrame(columns=BASE_COLUMNS))
else:
    st.caption('Use your own permitted listing export. Property types use the labels from the calculator. Rates and selling-cost percentages are decimals (0.08 = 8%). Every cost must be explicitly entered, including confirmed zero costs.')
    template = pd.DataFrame(columns=list(dict.fromkeys(BASE_COLUMNS + UNDERWRITING_COLUMNS)))
    st.download_button('Download blank listing/underwriting CSV', template.to_csv(index=False), 'property-intake-template.csv', 'text/csv')
    upload = st.file_uploader('Upload listings or completed underwriting worksheet', type='csv')
    frame = pd.DataFrame(columns=BASE_COLUMNS)
    if upload:
        try:
            frame = pd.read_csv(upload, dtype={'listing_id': 'string'})
        except (ValueError, UnicodeDecodeError):
            st.error('Unable to read this CSV. Use the provided template.')
if not frame.empty:
    try:
        results = screen_listings(frame, limits)
    except ListingError as exc:
        st.error(str(exc))
        st.stop()
    st.subheader(f'{len(results)} listings screened')
    st.dataframe(results.groupby('screen_status').size().rename('count').reset_index(), hide_index=True)
    display = [c for c in ['listing_id', 'address', 'state', 'property_type', 'asking_price', 'screen_status', 'reasons', 'net_profit', 'net_roi_pct', 'last_seen_date', 'source'] if c in results]
    st.dataframe(results[display].sort_values('net_roi_pct', ascending=False, na_position='last'), hide_index=True)
    st.download_button('Download screening results', results.to_csv(index=False), 'property-screen-results.csv', 'text/csv')
    st.download_button('Download underwriting worksheet', worksheet(frame).to_csv(index=False), 'property-underwriting.csv', 'text/csv')
    st.caption('Fill the worksheet and re-upload under CSV upload. Financing is never assumed to be offered by a seller. Source URLs record provenance; their content and comparability must still be independently checked. Active/last-seen dates reflect the source, not direct seller confirmation.')
elif source == 'CSV upload':
    st.info('Upload a listing file to begin. No fictional properties are shown as opportunities.')
