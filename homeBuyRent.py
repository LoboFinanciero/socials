import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Mexico Buy vs Rent: 50Y Analysis", layout="wide")
st.title("🏡 The 50-Year Wealth Battle: Buying vs. Renting in Mexico")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Property & Mortgage")
    prop_price = st.number_input("Property Price (MXN)", value=5_000_000, step=100_000)
    down_payment_pct = st.slider("Down Payment (%)", 10, 50, 20)
    closing_costs_pct = st.slider("Closing Costs (ISAI, Notary) (%)", 4, 9, 6)
    mortgage_rate = st.slider("Mortgage Interest Rate (%)", 8.0, 14.0, 11.0) / 100
    loan_term_years = st.selectbox("Loan Term (Years)", [15, 20], index=1)
    
    st.header("2. Monthly Costs")
    initial_rent = st.number_input("Monthly Rent (Current)", value=22_000, step=1000)
    annual_maint_pct = st.slider("Annual Maint/Insurance (%)", 0.5, 2.0, 1.0) / 100
    
    st.header("3. Financial assumptions")
    inflation = st.slider("General Inflation (CPI) (%)", 2.0, 7.0, 4.5) / 100
    appreciation = st.slider("Home Appreciation (%)", 2.0, 10.0, 5.5) / 100
    rent_increase = st.slider("Annual Rent Increase (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Investment Return (Portfolio) (%)", 5.0, 15.0, 10.0) / 100
    
    st.header("4. Taxes & Regime")
    is_resico = st.checkbox("Are you in RESICO?", value=False)
    marginal_tax_rate = st.slider("ISR Bracket (%)", 20, 35, 30) / 100 if not is_resico else 0.02
    portfolio_tax_rate = st.slider("Portfolio Capital Gains Tax (%)", 0, 35, 10) / 100

# --- CALCULATIONS ---
down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val # What renter starts with

loan_amount = prop_price - down_payment_val
monthly_rate = mortgage_rate / 12
n_payments = loan_term_years * 12
monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)

# Arrays
months = 600
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
buyer_investments = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)

house_value[0] = prop_price
remaining_loan[0] = loan_amount
renter_investments[0] = initial_capital
current_rent = initial_rent

# --- SIMULATION ---
for m in range(1, months + 1):
    if m % 12 == 0:
        house_value[m] = house_value[m-1] * (1 + appreciation)
        current_rent *= (1 + rent_increase)
    else:
        house_value[m] = house_value[m-1]

    # Buyer Logic
    if m <= n_payments:
        interest_p = remaining_loan[m-1] * monthly_rate
        principal_p = monthly_mortgage - interest_p
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_p)
        
        tax_refund = 0
        if not is_resico and m % 12 == 4:
            real_int = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            tax_refund = min(real_int, 214000) * marginal_tax_rate
        
        buyer_outflow = monthly_mortgage + (house_value[m] * annual_maint_pct / 12)
        # The refund goes directly to reduce the debt
        remaining_loan[m] = max(0, remaining_loan[m-1] - tax_refund)
        # Buyer investments now only grow with interest (no new money until the loan is over)
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12)
    else:
        remaining_loan[m] = 0
        buyer_outflow = (house_value[m] * annual_maint_pct / 12)
        # THE PIVOT
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12) + monthly_mortgage

    # Renter Logic
    savings_potential = buyer_outflow - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + inv_return/12) + savings_potential

# --- POST-PROCESSING ---
df = pd.DataFrame({
    'Year': np.arange(months + 1) / 12,
    'Buyer_NW': (house_value - remaining_loan) + buyer_investments,
    'Renter_NW': renter_investments
})

# --- LIQUIDATION CALCULATIONS ---
final_year = 50
idx = months
# Renter Tax
renter_gains = renter_investments[idx] - initial_capital
renter_tax = max(0, renter_gains * portfolio_tax_rate)
net_renter_liquid = renter_investments[idx] - renter_tax

# Buyer Tax
house_profit = house_value[idx] - prop_price
# Primary Residence Exemption (approx 700k UDIS ~ 5.7M MXN)
exempt_profit = 5_700_000
taxable_house_profit = max(0, house_profit - exempt_profit)
house_tax = taxable_house_profit * 0.20 # Estimated 
net_buyer_liquid = (house_value[idx] - house_tax - (house_value[idx] * 0.04)) + (buyer_investments[idx] * 0.9)

# --- VISUALS ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Year'], y=df['Buyer_NW'], name='Buyer Total NW', line=dict(color='#00CC96')))
fig.add_trace(go.Scatter(x=df['Year'], y=df['Renter_NW'], name='Renter Total NW', line=dict(color='#636EFA')))
st.plotly_chart(fig, use_container_width=True)

# --- FINAL VERDICT ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.subheader("💰 Net Liquid Wealth (Year 50)")
    st.write("This is what you keep **after taxes and selling fees.**")
    st.metric("Buyer Liquid", f"${net_buyer_liquid:,.0f}")
    st.metric("Renter Liquid", f"${net_renter_liquid:,.0f}")

with c2:
    st.subheader("💡 The 'Aha' Moment")
    total_int = (monthly_mortgage * n_payments) - loan_amount
    total_rent = initial_rent * 12 * ((1 + rent_increase)**50 - 1) / rent_increase
    st.write(f"Total Rent Paid in 50 years: **${total_rent:,.0f}**")
    st.write(f"Total Interest Paid to Bank: **${total_int:,.0f}**")

st.info(f"Summary: In Year 50, the **{'Buyer' if net_buyer_liquid > net_renter_liquid else 'Renter'}** wins the game.")
