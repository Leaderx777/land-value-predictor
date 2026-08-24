from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from train import FEATURES, MODEL_PATH

st.set_page_config(page_title="Land Value Predictor", layout="centered")
st.title("Land Value Predictor")
st.caption("Machine-learning MVP using synthetic training data")

if not MODEL_PATH.exists():
    st.warning("Model artifact not found. Run `python train.py` first.")
    st.stop()

model = joblib.load(MODEL_PATH)

acres = st.number_input("Acres", min_value=0.1, value=5.0, step=0.5)
distance = st.number_input("Distance to city (miles)", min_value=0.0, value=12.0, step=1.0)
frontage = st.number_input("Road frontage (ft)", min_value=0.0, value=250.0, step=25.0)
zoning = st.slider("Zoning score", min_value=1, max_value=5, value=3)
utilities = st.selectbox("Utilities available", options=[0, 1], format_func=lambda x: "Yes" if x else "No")

row = pd.DataFrame(
    [[acres, distance, frontage, zoning, utilities]],
    columns=FEATURES,
)

if st.button("Estimate value", type="primary"):
    prediction = float(model.predict(row)[0])
    st.metric("Estimated land value", f"${prediction:,.0f}")
    st.info("Demo only: trained on synthetic data, not a real appraisal model.")
