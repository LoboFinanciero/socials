import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 2026 MEXICO CONSTANTS ---
UMA_ANUAL_2026 = 42794.64  # $117.31 * 364.8 approx
UDI_VAL_2026 = 8.6759      # Late Jan 2026 Value
VALOR_EXENCION_ISR = 700_000 * UDI_VAL_2026 

# --- CONFIGURATION ---
st.set_page_config(page_title="Mexico Buy vs Rent: 2026", layout="wide")
st.title("🏡 The Wealth Battle: Buying vs. Renting in Mexico")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("🏠 1. Buyer Profile")
    prop_price = st.number_input("Property Price (MXN)", value=5_000_000, step=100_000)
    down_payment_pct = st.slider("Down Payment (%)", 10, 50, 20)
    closing_costs_pct = st.slider("Closing Costs (ISAI, Notary) (%)", 4, 9, 6)
    mortgage_rate = st.slider("Mortgage Interest Rate (%)", 8.0, 14.0, 11.0) / 100
    loan_term_years = st.selectbox("Loan Term (Years)", [15, 20], index=1)
    appreciation = st.slider("Home Appreciation (%)", 2.0, 10.0, 5.5) / 100
    annual_maint_pct = st.slider("Annual Maint/Insurance (%)", 0.5, 2.0, 1.0) / 100
    
    st.header("📉 2. Renter Profile")
    initial_rent = st.number_input("Monthly Rent (Current)", value=22_000, step=1000)
    rent_increase = st.slider("Annual Rent Increase (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Investment Return (Portfolio) (%)", 5.0, 15.0, 10.0) / 100
    
    st.header("⚖️ 3. Financials & Taxes")
    inflation = st.slider("General Inflation (CPI) (%)", 2.0, 7.0, 4.5) / 100
    annual_salary = st.number_input("Annual Gross Salary (MXN)", value=800_000, step=50_000)
    is_resico = st.checkbox("Are you in RESICO?", value=False)
    marginal_tax_rate = st.slider("ISR Bracket (%)", 20, 35, 30) / 100 if not is_resico else 0.02
    portfolio_tax_rate = st.slider("Portfolio Tax (%)", 0, 35, 10) / 100

# --- CALCULATIONS ---
down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val 

loan_amount = prop_price - down_payment_val
monthly_rate = mortgage_rate / 12
n_payments = loan_term_years * 12
monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
limite_deduccion = min(UMA_ANUAL_2026 * 5, annual_salary * 0.15)

# Arrays
months = 600
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
buyer_investments = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)
buyer_liquid_nw = np.zeros(months + 1)
renter_liquid_nw = np.zeros(months + 1)
buyer_sunk = np.zeros(months + 1)
renter_sunk = np.zeros(months + 1)

house_value[0], remaining_loan[0], renter_investments[0] = prop_price, loan_amount, initial_capital
current_rent = initial_rent

# --- UNIFIED SIMULATION ---
for m in range(1, months + 1):
    if m % 12 == 0:
        house_value[m] = house_value[m-1] * (1 + appreciation)
        current_rent *= (1 + rent_increase)
    else:
        house_value[m] = house_value[m-1]

    # Buyer Sunk Costs & Logic
    maint_p = (house_value[m] * annual_maint_pct) / 12
    predial_p = (house_value[m] * 0.002) / 12
    
    if m <= n_payments:
        int_p = remaining_loan[m-1] * monthly_rate
        remaining_loan[m] = max(0, remaining_loan[m-1] - (monthly_mortgage - int_p))
        
        real_int = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
        refund = (min(real_int, limite_deduccion) * marginal_tax_rate) if not is_resico and m % 12 == 4 else 0
        
        buyer_sunk[m] = int_p + maint_p + predial_p - (refund/12 if m % 12 == 4 else 0)
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12)
    else:
        remaining_loan[m] = 0
        buyer_sunk[m] = maint_p + predial_p
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12) + monthly_mortgage

    # Renter Logic
    renter_sunk[m] = current_rent
    savings = ((monthly_mortgage if m <= n_payments else 0) + maint_p + predial_p) - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + inv_return/12) + savings

    # Fair Liquidation (Net Value after 6%+IVA agent fee and ISR)
    net_sale = house_value[m] * 0.9304 
    isr_house = max(0, (net_sale - prop_price) - VALOR_EXENCION_ISR) * 0.20
    buyer_liquid_nw[m] = (net_sale - remaining_loan[m] - isr_house) + (buyer_investments[m] * 0.9)
    
    renter_gains = max(0, renter_investments[m] - initial_capital)
    renter_liquid_nw[m] = renter_investments[m] - (renter_gains * portfolio_tax_rate)

# --- VISUALS ---
df = pd.DataFrame({'Year': np.arange(months + 1) / 12})
fig_nw = go.Figure()
fig_nw.add_trace(go.Scatter(x=df['Year'], y=buyer_liquid_nw, name='Buyer (Green)', line=dict(color='#00CC96', width=3)))
fig_nw.add_trace(go.Scatter(x=df['Year'], y=renter_liquid_nw, name='Renter (Blue)', line=dict(color='#636EFA', width=3)))
st.plotly_chart(fig_nw, use_container_width=True)

fig_sunk = go.Figure()
fig_sunk.add_trace(go.Scatter(x=df['Year'], y=buyer_sunk, name='Buyer Sunk', line=dict(color='#00CC96', width=2)))
fig_sunk.add_trace(go.Scatter(x=df['Year'], y=renter_sunk, name='Renter Sunk', line=dict(color='#636EFA', dash='dash')))
st.plotly_chart(fig_sunk, use_container_width=True)

# --- MILESTONES ---
st.divider()
st.header("🎯 Key Decision Milestones")
c_be = next((i/12 for i in range(12, months) if buyer_sunk[i] < renter_sunk[i]), None)
w_be = next((i/12 for i in range(24, months) if buyer_liquid_nw[i] > renter_liquid_nw[i]), None)

col1, col2 = st.columns(2)
col1.metric("Monthly Cost Parity", f"{c_be:.1f} Years" if c_be else "Never")
col2.metric("Wealth Breakeven", f"{w_be:.1f} Years" if w_be else "Never")

st.subheader("💰 Cash-in-Hand (Year 10)")
col3, col4 = st.columns(2)
col3.metric("Buyer's Liquid Wealth", f"${buyer_liquid_nw[120]:,.0f}")
col4.metric("Renter's Liquid Wealth", f"${renter_liquid_nw[120]:,.0f}")
