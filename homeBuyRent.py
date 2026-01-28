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
    annual_salary = st.sidebar.number_input("Annual Gross Salary (MXN)", value=800_000, step=50_000)
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
            # Official 2026 UMA: $117.31 daily / $42,794.64 annual
            uma_anual_2026 = 42794.64
            limite_5_umas = uma_anual_2026 * 5 # Approx $213,973
            limite_15_pct = annual_salary * 0.15
            cap_deduccion = min(limite_5_umas, limite_15_pct)

            real_int = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            # The refund is limited by the lesser of 15% salary or 5 UMAs
            tax_refund = min(real_int, cap_deduccion) * marginal_tax_rate
        
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

# --- UPDATED LIQUIDATION LOGIC ---
buyer_liquid_nw = np.zeros(months + 1)
renter_liquid_nw = np.zeros(months + 1)

# Jan 2026 Constants
udi_val = 8.6759
exencion_isr = 700_000 * udi_val

for m in range(months + 1):
    # 1. Renter Liquidation (Portfolio tax on gains)
    gains_renter = max(0, renter_investments[m] - initial_capital)
    renter_liquid_nw[m] = renter_investments[m] - (gains_renter * portfolio_tax_rate)
    
    # 2. Buyer Liquidation
    # House Sale: Value - Selling Costs (Notary/Commission ~6%)
    net_sale_price = house_value[m] * 0.94 
    profit = max(0, net_sale_price - prop_price)
    
    # ISR on House: Only on profit above 700k UDIs
    taxable_profit = max(0, profit - exencion_isr)
    # Using a 20% effective rate for taxable surplus as a safe proxy
    house_isr = taxable_profit * 0.20 
    
    # Buyer Investments (Taxed at withdrawal)
    buyer_inv_liquid = buyer_investments[m] * 0.90 # Simple 10% tax proxy
    
    # Final Liquid NW
    buyer_liquid_nw[m] = (net_sale_price - remaining_loan[m] - house_isr) + buyer_inv_liquid

# --- UPDATED VISUALS ---
df_liquid = pd.DataFrame({
    'Year': np.arange(months + 1) / 12,
    'Buyer_Liquid': buyer_liquid_nw,
    'Renter_Liquid': renter_liquid_nw
})

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_liquid['Year'], y=df_liquid['Buyer_Liquid'], 
                         name='Buyer (Cash in Hand)', line=dict(color='#00CC96', width=3)))
fig.add_trace(go.Scatter(x=df_liquid['Year'], y=df_liquid['Renter_Liquid'], 
                         name='Renter (Cash in Hand)', line=dict(color='#636EFA', width=3)))

fig.update_layout(title="Net Wealth If You Cashed Out Today (Post-Tax & Fees)",
                  yaxis_title="MXN ($)", xaxis_title="Years")
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
