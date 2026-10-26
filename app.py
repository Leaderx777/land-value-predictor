"""Personal cash-resale land analyzer. Resale assumptions are entered, never invented."""
from dataclasses import replace
import json

import pandas as pd
import streamlit as st

from deal_finance import Deal
from deal_limits import Limits, PROPERTY_TYPES, STATES

st.set_page_config(page_title="Personal Property Deal Analyzer", layout="wide")
st.title("Personal Property Deal Analyzer")
st.caption("Buy with cash or seller financing. Sell for cash. ROI is per deal, before income tax.")
with st.sidebar:
    st.header("Your limits")
    st.caption("Enable only the limits you want. Property price and cash available are separate.")
    def optional_limit(label, default=0., enabled=False):
        use = st.checkbox("Limit " + label, value=enabled, key="use_" + label)
        value = st.number_input(label, min_value=0., value=float(default), disabled=not use, key="limit_" + label)
        return value if use else None
    max_price = optional_limit("Purchase price ($)")
    max_upfront = optional_limit("Upfront cash ($)")
    max_total = optional_limit("Peak deal cash ($)")
    max_monthly = optional_limit("Monthly payment + holding ($)")
    min_roi = optional_limit("Minimum net ROI (%)", 30., True)
    min_profit = optional_limit("Minimum net profit ($)")
    use_months = st.checkbox("Limit holding time", key="use_months")
    max_months = st.number_input("Maximum holding months", min_value=0, value=12, disabled=not use_months)
    use_states = st.checkbox("Limit states", key="use_states")
    chosen_states = st.multiselect("Allowed states", STATES, disabled=not use_states)
    use_types = st.checkbox("Limit property types", key="use_types")
    chosen_types = st.multiselect("Allowed property types", PROPERTY_TYPES, default=list(PROPERTY_TYPES), disabled=not use_types)
    financing_filter = st.selectbox("Purchase financing allowed", ["Either", "Cash purchase", "Seller-financed purchase"])
    limits = Limits(max_price, max_upfront, max_total, max_monthly, min_roi, min_profit,
                    int(max_months) if use_months else None,
                    tuple(chosen_states) if use_states else None,
                    tuple(chosen_types) if use_types else None, financing_filter)
    st.session_state["active_limits"] = limits.to_dict()
    st.download_button("Save limits as JSON", json.dumps(limits.to_dict(), indent=2), "property-search-limits.json", "application/json")
    st.page_link("pages/1_Property_Search.py", label="Search listings / upload properties")
st.info("Enter a resale price supported by closed comparable sales. This calculator does not validate market value.")
with st.form("deal"):
    buy, sell = st.columns(2)
    with buy:
        st.subheader("Purchase")
        property_type = st.selectbox("Property type", PROPERTY_TYPES)
        state = st.selectbox("Property state", STATES, index=STATES.index("IL"))
        price = st.number_input("Purchase price ($)", min_value=0., value=0., step=500.)
        financed = st.checkbox("Use seller financing for my purchase")
        down = st.number_input("Purchase down payment ($; used only if financed)", min_value=0., value=0., step=100.)
        rate = st.number_input("Purchase note annual interest (%)", min_value=0., max_value=100., value=0.)
        term = st.number_input("Purchase amortization (months)", min_value=1, max_value=600, value=120)
        balloon = st.number_input("Purchase balloon month (0 = none)", min_value=0, max_value=600, value=0)
        closing = st.number_input("Buying closing costs and loan fees ($)", min_value=0., value=0.)
        improvements = st.number_input("Improvements and due diligence ($)", min_value=0., value=0.)
    with sell:
        st.subheader("Cash resale")
        resale = st.number_input("Expected cash resale price ($)", min_value=0., value=0., step=500.)
        months = st.number_input("Months until resale", min_value=0, max_value=600, value=6)
        holding = st.number_input("Monthly taxes, insurance and maintenance ($)", min_value=0., value=0.)
        selling_pct = st.number_input("Selling costs (% of resale price)", min_value=0., max_value=100., value=0.)
        selling_fixed = st.number_input("Other selling costs and payoff fees ($)", min_value=0., value=0.)

    submitted = st.form_submit_button("Analyze deal", type="primary")
if submitted:
    st.session_state["has_analyzed_deal"] = True
if st.session_state.get("has_analyzed_deal", False):
    deal = Deal(price, down if financed else price, rate / 100, int(term), int(balloon), resale,
                int(months), closing, improvements, selling_pct / 100, selling_fixed, holding)
    try:
        result = deal.analyze()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    a, b, c, d = st.columns(4)
    a.metric("Net profit before tax", f"${result['profit']:,.2f}")
    b.metric("Net project ROI", f"{result['project_roi_pct']:.1f}%")
    c.metric("Break-even cash resale", f"${result['break_even_resale']:,.2f}" if result['break_even_resale'] is not None else "No price-only break-even")
    d.metric("Peak additional cash required", f"${result['peak_funding']:,.2f}")
    checks = limits.check(deal, result, state=state, property_type=property_type)
    passes = all(row['passed'] for row in checks)
    if not checks:
        st.info("All limits are off. No pass/fail assessment is applied.")
    elif passes:
        st.success("Passes your enabled limits under these assumptions. Market value and property due diligence remain unverified.")
    else:
        st.warning("Does not pass all enabled limits. See the failed rules below.")
    if result['profit'] <= 0:
        st.warning("This scenario has no positive net profit.")
    if checks:
        st.subheader("Limit checks")
        table = pd.DataFrame(checks)
        table["actual"] = table["actual"].astype(str)
        table["limit"] = table["limit"].astype(str)
        st.dataframe(table, hide_index=True)
    if result['balloon_before_resale']:
        st.warning("The purchase balloon is due before resale. The cash-flow table assumes you fund it on time; refinancing is not assumed.")
    st.write(f"Purchase payment: ${result['regular_purchase_payment']:,.2f}/month · Note payoff at resale: ${result['purchase_payoff_at_resale']:,.2f} · Total deal costs: ${result['total_cost']:,.2f}")
    st.caption("Project ROI = net profit / all deal costs, including the full purchase price and financing interest. Cash ROI uses your cash contributions and can look higher with borrowing. Loan principal is not counted twice. Payoff follows the resale-month payment.")
    rows = []
    for label, scenario in [("Entered assumptions", deal), ("Resale price 10% lower", replace(deal, sale_price=resale * .9)),
                            ("Resale delayed 6 months", replace(deal, resale_month=min(600, int(months) + 6))),
                            ("Both changes", replace(deal, sale_price=resale * .9, resale_month=min(600, int(months) + 6)))]:
        r = scenario.analyze()
        rows.append({"Scenario": label, "Net profit ($)": r['profit'], "Net project ROI (%)": round(r['project_roi_pct'], 2),
                     "Peak cash needed ($)": r['peak_funding'], "All enabled limits met": all(c["passed"] for c in limits.check(scenario, r, state=state, property_type=property_type))})
    st.subheader("Downside scenarios")
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.subheader("Monthly cash flow")
    flow = pd.DataFrame(result['flows'])
    st.dataframe(flow, hide_index=True)
    st.download_button("Download cash-flow CSV", flow.to_csv(index=False), "land-deal-cash-flow.csv", "text/csv")
    st.caption("Assumes a cash sale closes at the entered price/date, payments are current and the purchase note permits the modeled payoff. Costs are your inputs; defaults of zero do not mean costs are absent. No appreciation, refinancing, income tax, default, or legal/title outcome is assumed.")
