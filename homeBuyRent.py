import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
    appreciation_annual = st.slider("Home Appreciation (%)", 2.0, 10.0, 5.5) / 100
    annual_maint_pct = st.slider("Annual Maint/Insurance (%)", 0.5, 2.0, 1.0) / 100
    
    st.header("📉 2. Renter Profile")
    initial_rent = st.number_input("Monthly Rent (Current)", value=22_000, step=1000)
    rent_increase_annual = st.slider("Annual Rent Increase (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Investment Return (Portfolio) (%)", 5.0, 15.0, 10.0) / 100
    
    st.header("⚖️ 3. Financials & Taxes")
    inflation = st.slider("General Inflation (CPI) (%)", 2.0, 7.0, 4.5) / 100
    annual_salary = st.number_input("Annual Gross Salary (MXN)", value=800_000, step=50_000)
    is_resico = st.checkbox("Are you in RESICO?", value=False)
    
    marginal_tax_rate = 0.02 if is_resico else st.slider("Your ISR Bracket (%)", 20, 35, 30) / 100
    portfolio_tax_rate = st.slider("Portfolio Capital Gains Tax (%)", 0, 35, 10) / 100

# --- INITIAL CONSTANTS ---
months = 600
n_payments = loan_term_years * 12
down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val 

loan_amount = prop_price - down_payment_val
m_rate = mortgage_rate / 12
monthly_mortgage = loan_amount * (m_rate * (1 + m_rate)**n_payments) / ((1 + m_rate)**n_payments - 1)

# --- SIMULATION ARRAYS ---
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)
buyer_sunk = np.zeros(months + 1)
renter_sunk = np.zeros(months + 1)
monthly_rents = np.zeros(months + 1)

house_value[0] = prop_price
remaining_loan[0] = loan_amount
renter_investments[0] = initial_capital # Renter starts with the cash the buyer "lost" to downpayment/closing

current_rent = initial_rent
uma_anual_2026 = 42794.64
cap_deduccion = min(uma_anual_2026 * 5, annual_salary * 0.15)
predial_rate = 0.002 / 12

# --- SIMULATION LOOP ---
for m in range(1, months + 1):
    # 1. Yearly "Step" Logic
    # Every 12 months, the value and rent "jump"
    if m % 12 == 1 and m > 1:
        house_value[m] = house_value[m-1] * (1 + appreciation_annual)
        current_rent *= (1 + rent_increase_annual)
    else:
        house_value[m] = house_value[m-1]

    monthly_rents[m] = current_rent

    # 2. Buyer Logic (Mortgage & Sunk Costs)
    maint_costs = (house_value[m] * annual_maint_pct) / 12
    if m <= n_payments:
        interest_p = remaining_loan[m-1] * m_rate
        principal_p = monthly_mortgage - interest_p
        
        # Yearly Tax Refund (applied every 12th month)
        tax_refund = 0
        if not is_resico and m % 12 == 0:
            real_int_annual = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            tax_refund = min(real_int_annual, cap_deduccion) * marginal_tax_rate
        
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_p - tax_refund)
        buyer_sunk[m] = interest_p + maint_costs + (house_value[m] * predial_rate) - (tax_refund / 12)
        buyer_outflow = monthly_mortgage + maint_costs
    else:
        remaining_loan[m] = 0
        buyer_sunk[m] = maint_costs + (house_value[m] * predial_rate)
        buyer_outflow = maint_costs

    # 3. Renter Logic (Wealth accumulation)
    # The renter invests the difference between the Buyer's total outflow and their rent
    savings_potential = buyer_outflow - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + inv_return/12) + savings_potential
    renter_sunk[m] = current_rent

# --- VECTORIZED LIQUIDATION (Taxes & Fees) ---
udi_val = 8.6759
exencion_isr = 700_000 * udi_val
years_arr = np.arange(months + 1) / 12

# Buyer Net Wealth: House Value - Loan - Selling Fees (6%) - ISR on Gains
net_sale_price = house_value * 0.94 
house_profit = np.maximum(0, net_sale_price - prop_price)
taxable_profit = np.maximum(0, house_profit - exencion_isr)
house_isr = taxable_profit * 0.20
buyer_liquid_nw = net_sale_price - remaining_loan - house_isr

# Renter Net Wealth: Total Portfolio - 10% Capital Gains Tax on profit
renter_gains = np.maximum(0, renter_investments - initial_capital)
renter_liquid_nw = renter_investments - (renter_gains * portfolio_tax_rate)

# --- CHARTS ---
fig_nw = go.Figure()
fig_nw.add_trace(go.Scatter(x=years_arr, y=buyer_liquid_nw, name="Buyer (Home Equity)", line=dict(color='#00CC96', width=3)))
fig_nw.add_trace(go.Scatter(x=years_arr, y=renter_liquid_nw, name="Renter (Portfolio)", line=dict(color='#636EFA', width=3)))
fig_nw.update_layout(title="Net Wealth If You Sold Everything Today", template="plotly_dark")
st.plotly_chart(fig_nw, use_container_width=True)

fig_sunk = go.Figure()
fig_sunk.add_trace(go.Scatter(x=years_arr, y=buyer_sunk, name="Owner: Interest+Maint+Taxes", line=dict(color='#FF4B4B')))
fig_sunk.add_trace(go.Scatter(x=years_arr, y=renter_sunk, name="Renter: Pure Rent", line=dict(color='#636EFA')))
fig_sunk.update_layout(title="Monthly 'Lost' Money (Sunk Costs)", template="plotly_dark")
st.plotly_chart(fig_sunk, use_container_width=True)

# --- ADD THIS AFTER THE OTHER CHARTS ---

# 1. Calculate Total Monthly Outflow Arrays
buyer_outflow_monthly = np.zeros(months + 1)
for m in range(1, months + 1):
    maint = (house_value[m] * annual_maint_pct) / 12
    predial = (house_value[m] * predial_rate)
    
    # Monthly Refund logic (distributing the annual refund for the chart)
    # Note: In real life you get it once a year, but for a 'monthly spend' 
    # comparison, we average it out.
    temp_refund = 0
    if not is_resico and m <= n_payments:
        # We use the previous month's balance for the real interest calc
        real_int_annual = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
        temp_refund = (min(real_int_annual, cap_deduccion) * marginal_tax_rate) / 12

    if m <= n_payments:
        buyer_outflow_monthly[m] = monthly_mortgage + maint + predial - temp_refund
    else:
        # Post-mortgage life!
        buyer_outflow_monthly[m] = maint + predial

# 2. Renter Outflow is just the 'current_rent' array we already have
# (Need to make sure we use the version that captures the yearly steps)
renter_outflow_monthly = monthly_rents # Created in the previous block

# 3. PLOT: Total Monthly Outflow
fig_outflow = go.Figure()

fig_outflow.add_trace(go.Scatter(
    x=years_arr, 
    y=buyer_outflow_monthly, 
    name="Buyer: Total Monthly Spend", 
    line=dict(color='#00CC96', width=3)
))

fig_outflow.add_trace(go.Scatter(
    x=years_arr, 
    y=renter_outflow_monthly, 
    name="Renter: Monthly Rent", 
    line=dict(color='#636EFA', width=3, dash='dash')
))

fig_outflow.update_layout(
    title="Total Monthly Out-of-Pocket Cost (Cash Flow)",
    yaxis_title="MXN ($)",
    xaxis_title="Years",
    template="plotly_dark",
    hovermode="x unified"
)

st.plotly_chart(fig_outflow, use_container_width=True)

st.divider()
st.header("🎯 The Verdict: When does Buying Win?")

# 1. Calculation: Monthly Cash Flow Breakeven 
# (When is Mortgage + Maint > Rent?)
cash_breakeven_year = None
for i in range(1, len(buyer_outflow_monthly)):
    if renter_outflow_monthly[i] > buyer_outflow_monthly[i]:
        cash_breakeven_year = i / 12
        break

# 2. Calculation: Sunk Cost Breakeven 
# (When is Rent > Interest + Maint?)
sunk_breakeven_year = None
for i in range(1, len(buyer_sunk)):
    if renter_sunk[i] > buyer_sunk[i]:
        sunk_breakeven_year = i / 12
        break

# 3. Calculation: Wealth Breakeven 
# (When is House Equity > Renter Portfolio?)
wealth_breakeven_year = None
for i in range(12, len(buyer_liquid_nw)): # Start checking after 1 year
    if buyer_liquid_nw[i] > renter_liquid_nw[i]:
        wealth_breakeven_year = i / 12
        break

# Display Metrics
c1, c2, c3 = st.columns(3)

with c1:
    val_cash = f"{cash_breakeven_year:.1f} Years" if cash_breakeven_year else "Never"
    st.metric("Monthly Budget Parity", val_cash)
    st.caption("When your monthly rent finally becomes higher than the mortgage payment.")

with c2:
    val_sunk = f"{sunk_breakeven_year:.1f} Years" if sunk_breakeven_year else "Never"
    st.metric("The 'Waste' Breakeven", val_sunk)
    st.caption("When rent (100% loss) exceeds the interest and maintenance you 'lose' as an owner.")

with c3:
    val_wealth = f"{wealth_breakeven_year:.1f} Years" if wealth_breakeven_year else "Never"
    st.metric("Total Wealth Parity", val_wealth)
    st.caption("The moment you are officially richer as an owner than as a renter.")
