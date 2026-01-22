import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Buy vs Rent Mexico: 50-Year Analysis", layout="wide")
st.title("🏡 Buy vs. Rent: The 50-Year Net Worth Battle (Mexico Edition)")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("1. Property Details (MXN)")
    prop_price = st.number_input("Property Price", value=5_000_000, step=100_000)
    down_payment_pct = st.slider("Down Payment (%)", 10, 50, 20)
    closing_costs_pct = st.slider("Closing Costs (ISAI, Notary) (%)", 4, 9, 6)
    mortgage_rate = st.slider("Mortgage Interest Rate (%)", 8.0, 14.0, 11.0) / 100
    loan_term_years = st.selectbox("Loan Term (Years)", [15, 20], index=1)
    
    st.header("2. Monthly Costs & Rent")
    initial_rent = st.number_input("Monthly Rent for similar property", value=22_000, step=1000)
    annual_maint_pct = st.slider("Annual Maintenance/Insurance (%)", 0.5, 2.0, 1.0) / 100
    
    st.header("3. Financial Assumptions")
    inflation = st.slider("Expected Annual Inflation (%)", 3.0, 7.0, 4.5) / 100
    appreciation = st.sidebar.slider("Annual Home Appreciation (%)", 2.0, 10.0, 6.0) / 100
    rent_increase = st.sidebar.slider("Annual Rent Increase (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Investment Return (e.g. S&P 500/CETES) (%)", 5.0, 15.0, 10.0) / 100
    marginal_tax_rate = st.slider("Your Tax Rate (ISR Bracket) (%)", 20, 35, 30) / 100

# --- CALCULATIONS ---
# Initial Cash Outlay
down_payment_val = prop_price * (down_payment_pct / 100)
closing_costs_val = prop_price * (closing_costs_pct / 100)
initial_capital = down_payment_val + closing_costs_val

# Mortgage Math (Fixed Rate Monthly)
loan_amount = prop_price - down_payment_val
monthly_rate = mortgage_rate / 12
n_payments = loan_term_years * 12
monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)

# Initialize Data Arrays for 50 Years (600 months)
months = 600
years = 50
time_axis = np.arange(months + 1)

# Buyer Data
house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
buyer_investments = np.zeros(months + 1)
house_value[0] = prop_price
remaining_loan[0] = loan_amount

# Renter Data
renter_investments = np.zeros(months + 1)
renter_investments[0] = initial_capital # Starts with what buyer spent on down+closing

# --- THE SIMULATION ENGINE ---
current_rent = initial_rent

for m in range(1, months + 1):
    # 1. Update House Value and Rent (Annual adjustments)
    if m % 12 == 0:
        house_value[m] = house_value[m-1] * (1 + appreciation)
        current_rent *= (1 + rent_increase) # Using the new rent_increase variable
    else:
        house_value[m] = house_value[m-1]
    
    # 2. Buyer Calculations
    if m <= n_payments:
        # Interest & Principal logic
        interest_payment = remaining_loan[m-1] * monthly_rate
        principal_payment = monthly_mortgage - interest_payment
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_payment)
        
        # SAT Tax Refund (Annual Injection)
        tax_refund = 0
        if m % 12 == 4:
            # Deducting Real Interest (Rate - Inflation)
            real_interest = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            deductible_amount = min(real_interest, 214000) # 2026 UMA Cap approx
            tax_refund = deductible_amount * marginal_tax_rate
        
        # Total Buyer Outflow (Cash leaving their pocket)
        buyer_monthly_outflow = monthly_mortgage + (house_value[m] * annual_maint_pct / 12)
        
        # Buyer's small investment portfolio (from tax refunds)
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12) + tax_refund
    else:
        # AFTER MORTGAGE: The "Pivot"
        remaining_loan[m] = 0
        # Buyer only pays maintenance now
        buyer_monthly_outflow = (house_value[m] * annual_maint_pct / 12)
        
        # Pivot: Buyer now invests what used to be their mortgage payment
        buyer_investments[m] = buyer_investments[m-1] * (1 + inv_return/12) + monthly_mortgage

    # 3. Renter Simulation (The "Matching" Principle)
    # The Renter's 'Savings Potential' is the Buyer's total outflow minus the Rent.
    # If the Buyer is spending $45k and Rent is $25k, the Renter invests $20k.
    # If later on Rent ($60k) is more than Buyer Maint ($5k), the savings become negative, 
    # meaning the Renter is pulling money OUT of their portfolio to pay rent.
    
    savings_potential = buyer_monthly_outflow - current_rent
    renter_investments[m] = renter_investments[m-1] * (1 + inv_return/12) + savings_potential

# Prepare DataFrame for Plotly
df = pd.DataFrame({
    'Year': time_axis / 12,
    'Buyer Net Worth': (house_value - remaining_loan) + buyer_investments,
    'Renter Net Worth': renter_investments
})

# --- VISUALIZATION ---
st.header("Net Worth Comparison: 50 Year Horizon")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Year'], y=df['Buyer Net Worth'], name='Buyer (Equity + Investments)', line=dict(color='#00CC96', width=3)))
fig.add_trace(go.Scatter(x=df['Year'], y=df['Renter Net Worth'], name='Renter (Investment Portfolio)', line=dict(color='#636EFA', width=3)))

fig.update_layout(
    hovermode="x unified",
    yaxis_title="Total Net Worth (MXN)",
    xaxis_title="Years",
    template="plotly_white",
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# --- CONCLUSION BOX ---
y50_buyer = df['Buyer Net Worth'].iloc[-1]
y50_renter = df['Renter Net Worth'].iloc[-1]
winner = "Buyer" if y50_buyer > y50_renter else "Renter"

col1, col2, col3 = st.columns(3)
col1.metric("Buyer Year 50", f"${y50_buyer:,.0f}")
col2.metric("Renter Year 50", f"${y50_renter:,.0f}")
col3.info(f"The long-term winner is the **{winner}**.")

# --- ADVANCED METRICS ---
st.divider()
st.header("The Verdict: Deep Dive")

# 1. Breakeven Year Calculation
cross_over_year = "Never"
for i in range(1, len(df)):
    if df['Buyer Net Worth'].iloc[i] > df['Renter Net Worth'].iloc[i]:
        cross_over_year = f"Year {df['Year'].iloc[i]:.1f}"
        break

# 2. Total "Money Lost" Calculation
total_rent_paid = initial_rent * 12 * ((1 + inflation)**years - 1) / inflation
# Interest is harder; we sum it during the mortgage period
total_interest_paid = 0
temp_loan = loan_amount
for _ in range(n_payments):
    interest = temp_loan * monthly_rate
    total_interest_paid += interest
    temp_loan -= (monthly_mortgage - interest)

# 3. Displaying the Conclusion Cards
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("⏳ Breakeven")
    st.metric("Buying wins at:", cross_over_year)
    st.caption("If you plan to move before this year, Renting is mathematically superior.")

with c2:
    st.subheader("💸 'Money Lost'")
    st.write(f"**Total Rent Paid:** ${total_rent_paid:,.0f}")
    st.write(f"**Total Interest Paid:** ${total_interest_paid:,.0f}")
    st.caption("Both options involve 'losing' money; the question is which one loses less.")

with c3:
    st.subheader("📈 Real Growth")
    roi_gap = (inv_return - appreciation) * 100
    st.write(f"**Yield Gap:** {roi_gap:.1f}%")
    if roi_gap > 4:
        st.warning("The 'Opportunity Cost' of your down payment is very high. Your investments need to work hard to beat the house.")
    else:
        st.success("House appreciation is keeping pace with the market. Buying looks solid.")

# 4. Final Recommendation Text
st.markdown("---")
if cross_over_year == "Never":
    st.error("### 🚩 Verdict: Rent & Invest")
    st.write("Under these specific parameters (likely high interest rates or low rent), the buyer never catches up to the renter's compounded portfolio.")
else:
    st.success(f"### ✅ Verdict: Buy (if staying {cross_over_year}+)")
    st.write(f"Buying is a wealth-building tool for you, but only in the long run. Between now and {cross_over_year}, the renter will actually have a higher net worth.")

st.markdown(f"""
### Key Insights for Mexico
* **The SAT Advantage:** Your mortgage interest deduction (Real Interest) acts as a yearly 'bonus' reinvested into your net worth.
* **The Tipping Point:** Notice the slope change for the Buyer at Year {loan_term_years}. This is when you stop paying the bank and start paying yourself.
* **Liquidity:** The Renter's wealth is 100% liquid (cash/stocks). The Buyer's wealth is heavily tied to the physical house until Year 50.
""")

# Create a summary table every 5 years
summary_data = df[df['Year'] % 5 == 0].copy()
summary_data['Buyer Net Worth'] = summary_data['Buyer Net Worth'].map('${:,.0f}'.format)
summary_data['Renter Net Worth'] = summary_data['Renter Net Worth'].map('${:,.0f}'.format)

st.subheader("📋 5-Year Snapshot")
st.table(summary_data[['Year', 'Buyer Net Worth', 'Renter Net Worth']])
