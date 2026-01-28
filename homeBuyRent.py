import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Mexico Buy vs Rent: 50Y Analysis", layout="wide")
st.title("🏡 The 50-Year Wealth Battle: Mexico Edition")

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
    
    marginal_tax_rate = 0.02 if is_resico else st.slider("Your ISR Bracket (%)", 20, 35, 30) / 100
    portfolio_tax_rate = st.slider("Portfolio Capital Gains Tax (%)", 0, 35, 10) / 100

# --- CALCULATIONS ---
# Pre-calculating monthly rates for smoother compounding
monthly_appreciation = (1 + appreciation)**(1/12) - 1
monthly_rent_increase = (1 + rent_increase)**(1/12) - 1
monthly_inv_return = (1 + inv_return)**(1/12) - 1

down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val 

loan_amount = prop_price - down_payment_val
monthly_rate = mortgage_rate / 12
n_payments = loan_term_years * 12
monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)

# Initialize Arrays
months = 600
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
buyer_investments = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)
buyer_sunk = np.zeros(months + 1)
renter_sunk = np.zeros(months + 1)

house_value[0] = prop_price
remaining_loan[0] = loan_amount
renter_investments[0] = initial_capital
current_rent = initial_rent

# Mexico Tax Constants (2026 Estimates)
uma_anual_2026 = 42794.64
cap_deduccion = min(uma_anual_2026 * 5, annual_salary * 0.15)
predial_rate = 0.002 / 12 # Monthly predial

# --- SIMULATION ---
for m in range(1, months + 1):
    # Property & Rent Growth
    house_value[m] = house_value[m-1] * (1 + monthly_appreciation)
    current_rent *= (1 + monthly_rent_increase)
    
    # 1. BUYER LOGIC
    if m <= n_payments:
        interest_p = remaining_loan[m-1] * monthly_rate
        principal_p = monthly_mortgage - interest_p
        
        # Real Interest Tax Deduction (Annualized check)
        tax_refund = 0
        if not is_resico and m % 12 == 0:
            # Simplified: Real interest is (Rate - Inflation)
            real_int_annual = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            tax_refund = min(real_int_annual, cap_deduccion) * marginal_tax_rate
        
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_p - tax_refund)
        maint = (house_value[m] * annual_maint_pct / 12)
        buyer_outflow = monthly_mortgage + maint
        
        # Sunk Costs
        buyer_sunk[m] = interest_p + maint + (house_value[m] * predial_rate) - (tax_refund / 12)
        buyer_investments[m] = buyer_investments[m-1] * (1 + monthly_inv_return)
    else:
        remaining_loan[m] = 0
        maint = (house_value[m] * annual_maint_pct / 12)
        buyer_outflow = maint
        buyer_sunk[m] = maint + (house_value[m] * predial_rate)
        # The Pivot: Mortgage money now goes to investments
        buyer_investments[m] = buyer_investments[m-1] * (1 + monthly_inv_return) + monthly_mortgage

    # 2. RENTER LOGIC
    savings_potential = buyer_outflow - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + monthly_inv_return) + savings_potential
    renter_sunk[m] = current_rent

# --- LIQUIDATION LOGIC ---
udi_val = 8.6759 # Jan 2026
exencion_isr = 700_000 * udi_val

# Vectorized Liquidation
net_sale_price = house_value * 0.94 # 6% commissions/fees
house_profit = np.maximum(0, net_sale_price - prop_price)
taxable_house_profit = np.maximum(0, house_profit - exencion_isr)
house_isr = taxable_house_profit * 0.20

buyer_inv_liquid = buyer_investments * (1 - (portfolio_tax_rate * 0.5)) # Est. tax on gains only
buyer_liquid_nw = (net_sale_price - remaining_loan - house_isr) + buyer_inv_liquid

renter_inv_gains = np.maximum(0, renter_investments - initial_capital)
renter_liquid_nw = renter_investments - (renter_inv_gains * portfolio_tax_rate)

# --- VISUALS ---
years_arr = np.arange(months + 1) / 12
fig = go.Figure()
fig.add_trace(go.Scatter(x=years_arr, y=buyer_liquid_nw, name='Buyer Net Wealth', line=dict(color='#00CC96')))
fig.add_trace(go.Scatter(x=years_arr, y=renter_liquid_nw, name='Renter Net Wealth', line=dict(color='#636EFA')))
fig.update_layout(title="Total Liquid Wealth Over Time", yaxis_title="MXN", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

# Sunk Cost Chart
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=years_arr, y=buyer_sunk, name='Buyer (Interest+Maint)', line=dict(color='#FF4B4B')))
fig2.add_trace(go.Scatter(x=years_arr, y=renter_sunk, name='Renter (Rent)', line=dict(color='#636EFA')))
fig2.update_layout(title="Monthly Sunk Costs", yaxis_title="MXN", template="plotly_dark")
st.plotly_chart(fig2, use_container_width=True)
