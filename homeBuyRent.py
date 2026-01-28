import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Mexico Buy vs Rent", layout="wide")

# --- INPUTS (Simplified) ---
with st.sidebar:
    prop_price = st.number_input("Property Price (MXN)", value=5_000_000)
    mortgage_rate = st.slider("Mortgage Rate (%)", 8.0, 14.0, 11.0) / 100
    rent_increase_annual = st.slider("Annual Rent Increase (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Renter's Portfolio Return (%)", 5.0, 15.0, 10.0) / 100

# --- CALCULATIONS ---
months = 600
years = np.arange(months + 1) // 12
loan_term_months = 20 * 12

# 1. House Value (Yearly Steps)
# This creates a 'staircase' effect: value stays flat for 11 months, then jumps
house_value = prop_price * (1 + (st.sidebar.slider("Appreciation (%)", 0.0, 10.0, 5.0)/100))**years

# 2. Mortgage Logic (Fixed Payment)
loan_amount = prop_price * 0.8  # Assuming 20% down
m_rate = mortgage_rate / 12
pmt = loan_amount * (m_rate * (1 + m_rate)**loan_term_months) / ((1 + m_rate)**loan_term_months - 1)

# 3. Rent Logic (Yearly Steps)
# Rent stays flat for 12 months, then increases
monthly_rents = np.array([22000 * (1 + rent_increase_annual)**y for y in years])

# 4. Sunk Cost Comparison
# We calculate interest month-by-month because the balance drops
remaining_balance = loan_amount
buyer_sunk_costs = []
renter_portfolio = [prop_price * 0.26] # Down payment + Closing costs invested

for m in range(months + 1):
    # Buyer Sunk: Interest + 1% Annual Maint / 12
    interest_this_month = remaining_balance * m_rate if m <= loan_term_months else 0
    maint_this_month = (house_value[m] * 0.01) / 12
    buyer_sunk_costs.append(interest_this_month + maint_this_month)
    
    # Amortize loan
    principal_paid = pmt - interest_this_month if m <= loan_term_months else 0
    remaining_balance = max(0, remaining_balance - principal_paid)
    
    # Renter Wealth: Portfolio growth + (Mortgage PMT - Rent)
    if m > 0:
        # If Mortgage + Maint > Rent, Renter invests the difference
        buyer_total_outflow = (pmt if m <= loan_term_months else 0) + maint_this_month
        diff = buyer_total_outflow - monthly_rents[m]
        new_balance = renter_portfolio[-1] * (1 + inv_return/12) + diff
        renter_portfolio.append(new_balance)

# --- VISUALIZATION ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=np.arange(months+1)/12, y=house_value - remaining_balance, name="Owner Equity (House)"))
fig.add_trace(go.Scatter(x=np.arange(months+1)/12, y=renter_portfolio, name="Renter Portfolio"))
fig.update_layout(title="Equity vs. Portfolio (The 50Y Race)", xaxis_title="Years", yaxis_title="MXN")
st.plotly_chart(fig, use_container_width=True)
