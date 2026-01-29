import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="México Comprar vs Rentar: Análisis 50 Años", layout="wide")
st.title("🏡 ¿Comprar o Rentar en México?")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("🏠 1. Perfil del Comprador")
    prop_price = st.number_input("Precio de la Propiedad (MXN)", value=5_000_000, step=100_000)
    down_payment_pct = st.slider("Enganche (%)", 10, 50, 20)
    closing_costs_pct = st.slider("Costos de Cierre (ISAI, Notario) (%)", 4, 9, 6)
    mortgage_rate = st.slider("Tasa de Interés Hipotecario (%)", 8.0, 14.0, 11.0) / 100
    loan_term_years = st.selectbox("Plazo del Crédito (Años)", [15, 20], index=1)
    appreciation_annual = st.slider("Plusvalía Anual (%)", 2.0, 10.0, 5.5) / 100
    annual_maint_pct = st.slider("Mantenimiento/Seguro Anual (%)", 0.5, 2.0, 1.0) / 100
    
    st.header("📉 2. Perfil del Arrendatario")
    initial_rent = st.number_input("Renta Mensual (Actual)", value=22_000, step=1000)
    rent_increase_annual = st.slider("Incremento Anual de Renta (%)", 2.0, 10.0, 5.0) / 100
    inv_return = st.slider("Rendimiento de Inversión (Portafolio) (%)", 5.0, 15.0, 10.0) / 100
    
    st.header("⚖️ 3. Finanzas e Impuestos")
    inflation = st.slider("Inflación General (INPC) (%)", 2.0, 7.0, 4.5) / 100
    annual_salary = st.number_input("Salario Bruto Anual (MXN)", value=800_000, step=50_000)
    is_resico = st.checkbox("¿Estás en RESICO?", value=False)
    
    marginal_tax_rate = 0.02 if is_resico else st.slider("Tu Tasa de ISR (%)", 20, 35, 30) / 100
    portfolio_tax_rate = st.slider("Impuesto sobre Ganancias de Capital (%)", 0, 35, 10) / 100

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

uma_anual_2026 = 42794.64 
cap_deduccion = min(uma_anual_2026 * 5, annual_salary * 0.15)

house_value = np.zeros(months + 1)
remaining_loan = np.zeros(months + 1)
renter_investments = np.zeros(months + 1)
buyer_outflow_monthly = np.zeros(months + 1)
buyer_sunk = np.zeros(months + 1)
renter_sunk = np.zeros(months + 1)
monthly_rents = np.zeros(months + 1)
udi_arr = np.zeros(months + 1)

house_value[0] = prop_price
remaining_loan[0] = loan_amount
renter_investments[0] = initial_capital
udi_arr[0] = 8.6759 
monthly_rents[0] = initial_rent
current_rent = initial_rent
predial_rate = (0.002 / 12) * 0.6 

# --- SIMULATION LOOP ---
for m in range(1, months + 1):
    udi_arr[m] = udi_arr[m-1] * ((1 + inflation)**(1/12))
    house_value[m] = house_value[m-1] * ((1 + appreciation_annual)**(1/12))
    
    if m % 12 == 1 and m > 1:
        current_rent *= (1 + rent_increase_annual)
    monthly_rents[m] = current_rent

    maint_costs = (house_value[m] * annual_maint_pct) / 12
    monthly_predial = house_value[m] * predial_rate

    if m <= n_payments:
        interest_p = remaining_loan[m-1] * m_rate
        principal_p = monthly_mortgage - interest_p
        
        current_tax_refund = 0
        if not is_resico and m % 12 == 4:
            real_int_deductible = max(0, (mortgage_rate - inflation) * remaining_loan[m-1])
            current_tax_refund = min(real_int_deductible, cap_deduccion) * marginal_tax_rate
        
        remaining_loan[m] = max(0, remaining_loan[m-1] - principal_p - current_tax_refund)
        buyer_outflow_monthly[m] = monthly_mortgage + maint_costs + monthly_predial
        buyer_sunk[m] = interest_p + maint_costs + monthly_predial - (current_tax_refund / 12 if m % 12 == 4 else 0)
    else:
        remaining_loan[m] = 0
        buyer_outflow_monthly[m] = maint_costs + monthly_predial
        buyer_sunk[m] = maint_costs + monthly_predial

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
fig_nw.add_trace(go.Scatter(x=years_arr, y=buyer_liquid_nw, name="Comprador (Patrimonio Inmobiliario)", line=dict(color='#00CC96', width=3)))
fig_nw.add_trace(go.Scatter(x=years_arr, y=renter_liquid_nw, name="Arrendatario (Portafolio)", line=dict(color='#636EFA', width=3)))
fig_nw.update_layout(title="Patrimonio Neto Si Liquidaras Todo", template="plotly_dark", yaxis_title="MXN ($)")
st.plotly_chart(fig_nw, use_container_width=True)

fig_sunk = go.Figure()
fig_sunk.add_trace(go.Scatter(x=years_arr, y=buyer_sunk, name="Propietario: Intereses+Mant.+Impuestos", line=dict(color='#00CC96')))
fig_sunk.add_trace(go.Scatter(x=years_arr, y=renter_sunk, name="Arrendatario: Renta Pura", line=dict(color='#636EFA')))
fig_sunk.update_layout(title="Dinero 'Perdido' Mensual (Costos Hundidos)", template="plotly_dark", yaxis_title="MXN ($)")
st.plotly_chart(fig_sunk, use_container_width=True)

fig_outflow = go.Figure()
fig_outflow.add_trace(go.Scatter(x=years_arr, y=buyer_outflow_monthly, name="Comprador: Gasto Mensual", line=dict(color='#00CC96', width=3)))
fig_outflow.add_trace(go.Scatter(x=years_arr, y=monthly_rents, name="Arrendatario: Renta Mensual", line=dict(color='#636EFA', width=3)))
fig_outflow.update_layout(title="Comparación de Flujo de Efectivo (Gasto Mensual Corriente)", yaxis_title="MXN ($)", xaxis_title="Años", template="plotly_dark")
st.plotly_chart(fig_outflow, use_container_width=True)
st.caption("⚠️ Nota: Esta gráfica no incluye el pago inicial (enganche y escrituración) para mantener la escala visual, pero dichos montos están considerados en el cálculo de Riqueza Neta.")

# --- VERDICT ---
st.divider()
st.header("🎯 El Veredicto: ¿Cuándo Gana Comprar?")

cash_breakeven_year = next((i/12 for i in range(1, len(buyer_outflow_monthly)) if monthly_rents[i] > buyer_outflow_monthly[i]), None)
sunk_breakeven_year = next((i/12 for i in range(1, len(buyer_sunk)) if renter_sunk[i] > buyer_sunk[i]), None)
wealth_breakeven_year = next((i/12 for i in range(12, len(buyer_liquid_nw)) if buyer_liquid_nw[i] > renter_liquid_nw[i]), None)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Paridad de Presupuesto Mensual", f"{cash_breakeven_year:.1f} Años" if cash_breakeven_year else "Nunca")
    st.caption("Cuando la renta supera la hipoteca + gastos mensuales.")
with c2:
    st.metric("Equilibrio de 'Dinero Tirado'", f"{sunk_breakeven_year:.1f} Años" if sunk_breakeven_year else "Nunca")
    st.caption("Cuando la renta supera intereses y mantenimiento.")
with c3:
    st.metric("Paridad de Patrimonio Total", f"{wealth_breakeven_year:.1f} Años" if wealth_breakeven_year else "Nunca")
    st.caption("Cuando oficialmente eres más rico como propietario.")

with st.expander("📝 Ver Supuestos Detallados y Lógica Específica de México"):
    st.markdown("### 🛠️ El Motor Financiero")
    st.info("**Nota sobre Disciplina:** Este modelo asume que ambas partes son extremadamente disciplinadas. El Comprador usa cada centavo de su devolución de impuestos para reducir la deuda, y el Arrendatario invierte el 100% de sus ahorros potenciales en su portafolio sin falta.")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        **1. Propiedad e Impuestos**
        * **Devoluciones de Impuestos:** Basadas en 'Interés Real'. Solo aplica para empleados (*Sueldos y Salarios*).
        * **Estrategia de Devolución:** Modelada como pagos a capital anuales cada abril.
        * **Límites Fiscales:** Topados a 5 UMAs o 15% del ingreso.
        * **Exención:** Los primeros 700k UDIs de ganancia están libres de impuestos (UDI se ajusta mensualmente por inflación).
        * **Predial:** Estimado en 0.2% anual sobre un proxy de 60% del valor catastral.
        """)
    with col_b:
        st.markdown("""
        **2. Renta e Inversión**
        * **Capital Inicial:** El arrendatario comienza con el Enganche + Costos de Cierre del comprador.
        * **Costo de Oportunidad:** La diferencia mensual en gastos se invierte (o retira) del portafolio.
        * **Impuesto del Portafolio:** 10% de impuesto sobre ganancias (estándar para BMV).
        * **Costos de Venta:** 6% de comisión restada del Valor de la Propiedad al vender.
        """)
    st.write("---")
    st.caption(f"Parámetros del modelo basados en la Ley Fiscal Mexicana 2026. UDI Base: {udi_arr[0]:.4f}")
