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

# --- INITIAL CONSTANTS & ARRAYS ---
months = 600
years_arr = np.arange(months + 1) / 12
n_payments = loan_term_years * 12
down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val 

loan_amount = prop_price - down_payment_val
m_rate = mortgage_rate / 12 
monthly_mortgage = loan_amount * (m_rate * (1 + m_rate)**n_payments) / ((1 + m_rate)**n_payments - 1)

# Tax limits for Mexico 2026
uma_anual_2026 = 42794.64  # Estimated UMA for 2026
cap_deduccion = min(uma_anual_2026 * 5, annual_salary * 0.15)

# Initialize Arrays
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)
buyer_outflow_monthly = np.zeros(months + 1)
buyer_sunk = np.zeros(months + 1)
renter_sunk = np.zeros(months + 1)
monthly_rents = np.zeros(months + 1)
udi_arr = np.zeros(months + 1)

# Starting State
house_value[0] = prop_price
remaining_loan[0] = loan_amount
renter_investments[0] = initial_capital
udi_arr[0] = 8.6759 
current_rent = initial_rent
monthly_rents[0] = initial_rent
predial_rate = (0.002 / 12) * 0.6 # Adjusting for Cadastral value proxy

# --- SIMULATION LOOP ---
for m in range(1, months + 1):
    # 1. Update UDI and Asset Growth
    udi_arr[m] = udi_arr[m-1] * ((1 + inflation)**(1/12))
    house_value[m] = house_value[m-1] * ((1 + appreciation_annual)**(1/12))
    
    if m % 12 == 1 and m > 1:
        current_rent *= (1 + rent_increase_annual)
    monthly_rents[m] = current_rent

    # 2. Ownership Costs
    maint_costs = (house_value[m] * annual_maint_pct) / 12
    monthly_predial = house_value[m] * predial_rate

    # 3. Buyer Logic
    if m <= n_payments:
        interest_p = remaining_loan[m-1] * m_rate
        principal_p = monthly_mortgage - interest_p
        
        current_tax_refund = 0
        if not is_resico and m % 12 == 4:
            # Formula for Real Interest: (Nominal Rate - Inflation) * Balance
            real_int_deductible = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            current_tax_refund = min(real_int_deductible, cap_deduccion) * marginal_tax_rate
        
        # Apply refund to principal
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_p - current_tax_refund)
        buyer_outflow_monthly[m] = monthly_mortgage + maint_costs + monthly_predial
        
        # Sunk costs for the chart (Interest + Maint + Taxes - Refund benefit)
        buyer_sunk[m] = interest_p + maint_costs + monthly_predial - (current_tax_refund / 12 if m % 12 == 4 else 0)
    else:
        remaining_loan[m] = 0
        buyer_outflow_monthly[m] = maint_costs + monthly_predial
        buyer_sunk[m] = maint_costs + monthly_predial

    # 4. Renter Logic
    renter_sunk[m] = current_rent
    savings_potential = buyer_outflow_monthly[m] - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + inv_return/12) + savings_potential

# --- VECTORIZED LIQUIDATION ---
exencion_isr_dynamic = 700_000 * udi_arr
net_sale_price = house_value * 0.94 
house_profit = np.maximum(0, net_sale_price - prop_price)
taxable_profit = np.maximum(0, house_profit - exencion_isr_dynamic)
house_isr = taxable_profit * 0.20
buyer_liquid_nw = net_sale_price - remaining_loan - house_isr

renter_gains = np.maximum(0, renter_investments - initial_capital)
renter_liquid_nw = renter_investments - (renter_gains * portfolio_tax_rate)

# --- CHARTS ---
fig_nw = go.Figure()
fig_nw.add_trace(go.Scatter(x=years_arr, y=buyer_liquid_nw, name="Buyer (Home Equity)", line=dict(color='#00CC96', width=3)))
fig_nw.add_trace(go.Scatter(x=years_arr, y=renter_liquid_nw, name="Renter (Portfolio)", line=dict(color='#636EFA', width=3)))
fig_nw.update_layout(title="Net Wealth If You Sold Everything Today", template="plotly_dark", yaxis_title="MXN ($)")
st.plotly_chart(fig_nw, use_container_width=True)

fig_sunk = go.Figure()
fig_sunk.add_trace(go.Scatter(x=years_arr, y=buyer_sunk, name="Owner: Interest+Maint+Taxes", line=dict(color='#00CC96')))
fig_sunk.add_trace(go.Scatter(x=years_arr, y=renter_sunk, name="Renter: Pure Rent", line=dict(color='#636EFA')))
fig_sunk.update_layout(title="Monthly 'Lost' Money (Sunk Costs)", template="plotly_dark", yaxis_title="MXN ($)")
st.plotly_chart(fig_sunk, use_container_width=True)

# Monthly Outflow Array
buyer_outflow_monthly = np.zeros(months + 1)
for m in range(1, months + 1):
    maint = (house_value[m] * annual_maint_pct) / 12
    predial = (house_value[m] * predial_rate)
    temp_refund = 0
    if not is_resico and m <= n_payments:
        real_int_annual = max(0, (mortgage_rate - inflation) * remaining_loan[max(0, m-1)])
        temp_refund = (min(real_int_annual, cap_deduccion) * marginal_tax_rate) / 12

    if m <= n_payments:
        buyer_outflow_monthly[m] = monthly_mortgage + maint + predial - temp_refund
    else:
        buyer_outflow_monthly[m] = maint + predial

fig_outflow = go.Figure()
fig_outflow.add_trace(go.Scatter(x=years_arr, y=buyer_outflow_monthly, name="Buyer: Total Monthly Spend", line=dict(color='#00CC96', width=3)))
fig_outflow.add_trace(go.Scatter(x=years_arr, y=monthly_rents, name="Renter: Monthly Rent", line=dict(color='#636EFA', width=3)))
fig_outflow.update_layout(title="Total Monthly Out-of-Pocket Cost (Cash Flow)", yaxis_title="MXN ($)", xaxis_title="Years", template="plotly_dark")
st.plotly_chart(fig_outflow, use_container_width=True)

# --- VERDICT ---
st.divider()
st.header("🎯 The Verdict: When does Buying Win?")

cash_breakeven_year = next((i/12 for i in range(1, len(buyer_outflow_monthly)) if monthly_rents[i] > buyer_outflow_monthly[i]), None)
sunk_breakeven_year = next((i/12 for i in range(1, len(buyer_sunk)) if renter_sunk[i] > buyer_sunk[i]), None)
wealth_breakeven_year = next((i/12 for i in range(12, len(buyer_liquid_nw)) if buyer_liquid_nw[i] > renter_liquid_nw[i]), None)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Monthly Budget Parity", f"{cash_breakeven_year:.1f} Yrs" if cash_breakeven_year else "Never")
    st.caption("When rent exceeds the monthly mortgage + maint.")
with c2:
    st.metric("The 'Waste' Breakeven", f"{sunk_breakeven_year:.1f} Yrs" if sunk_breakeven_year else "Never")
    st.caption("When rent exceeds interest and maintenance.")
with c3:
    st.metric("Total Wealth Parity", f"{wealth_breakeven_year:.1f} Yrs" if wealth_breakeven_year else "Never")
    st.caption("When you're officially richer as an owner.")

with st.expander("📝 View Detailed Assumptions & Mexico-Specific Logic"):
    st.markdown("""
    **1. Tax Deductibility (ISR)**
    - Deducts 'Real Interest' only (Interest Rate - Inflation).
    - Capped at 5 UMAs or 15% of salary.
    - **Note:** Tax refunds are automatically modeled as extra payments to mortgage principal.
    
    **2. Selling the Property**
    - 6% sales commission is assumed.
    - First 700k UDIs of profit are tax-exempt (UDI grows with inflation).
    
    **3. Renter Portfolio**
    - Renter invests/draws the 'cash flow difference' vs the buyer.
    - 10% tax on all portfolio gains.
    """)
