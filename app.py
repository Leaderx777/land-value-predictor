"""Personal cash-resale land analyzer. Resale assumptions are entered, never invented."""
from dataclasses import replace

import pandas as pd
import streamlit as st

from deal_finance import Deal

st.set_page_config(page_title="Personal Land Deal Analyzer", layout="wide")
st.title("Personal Land Deal Analyzer")
st.caption("Buy with cash or seller financing. Sell for cash. ROI is per deal, before income tax.")
st.info("Enter a resale price supported by closed comparable sales. This calculator does not validate market value.")
with st.form("deal"):
    buy, sell = st.columns(2)
    with buy:
        st.subheader("Purchase")
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
        target = st.number_input("Target net project ROI (%)", min_value=0., value=30., step=5.)
        cash_limit = st.number_input("Available deal cash ($; 0 = not checked)", min_value=0., value=0.)
    submitted = st.form_submit_button("Analyze deal", type="primary")
if submitted:
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
    cash_ok = not cash_limit or result['peak_funding'] <= cash_limit
    passes = result['project_roi_pct'] >= target and result['profit'] > 0 and cash_ok
    if passes:
        st.success("Passes your entered ROI and cash limits under these assumptions. Market value and property due diligence remain unverified.")
    else:
        st.warning("Does not pass your entered ROI/cash limits.")
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
                     "Peak cash needed ($)": r['peak_funding'], "ROI target met": r['project_roi_pct'] >= target})
    st.subheader("Downside scenarios")
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.subheader("Monthly cash flow")
    flow = pd.DataFrame(result['flows'])
    st.dataframe(flow, hide_index=True)
    st.download_button("Download cash-flow CSV", flow.to_csv(index=False), "land-deal-cash-flow.csv", "text/csv")
    st.caption("Assumes a cash sale closes at the entered price/date, payments are current and the purchase note permits the modeled payoff. Costs are your inputs; defaults of zero do not mean costs are absent. No appreciation, refinancing, income tax, default, or legal/title outcome is assumed.")
