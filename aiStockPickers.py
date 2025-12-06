import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Batalla de Portafolios", layout="wide")

# 1. FECHA DE INICIO (HARD-CODED)
START_DATE = "2024-01-01"

PORTFOLIOS = {
    "ChatGPT": [
    "MSFT",  # Microsoft
    "NVDA",  # NVIDIA
    "GOOGL", # Alphabet
    "AMZN",  # Amazon
    "META",  # Meta Platforms
    "AAPL",  # Apple
    "TSLA",  # Tesla
    "INTC",  # Intel
    "PYPL",  # PayPal
    "EXC"    # Exelon
],
    "Gemini": [
    "VRT",   # Vertiv Holdings
    "FIX",   # Comfort Systems USA
    "CIEN",  # Ciena Corporation
    "APP",   # AppLovin
    "PLTR",  # Palantir Technologies
    "CRWD",  # CrowdStrike Holdings
    "SHOP",  # Shopify
    "DASH",  # DoorDash
    "UBER",  # Uber Technologies
    "HIMS"   # Hims & Hers Health
],
    "Fenrir": [
    "DBX",  # Dropbox
    "MTCH", # Match Group
    "GFS",  # GlobalFoundries
    "MRNA", # Moderna
    "PEGA", # Pegasystems
    "AMKR", # Amkor Technology
    "GTM",  # Granite Ridge (or ticker GTM depending on context)
    "BBWI", # Bath & Body Works
    "SMCI", # Super Micro Computer
    "ALGM"  # Allegro MicroSystems
], 
    "Benchmark": ["SPY"]
}

# --- FUNCIONES ---

def get_api_key():
    try:
        return st.secrets["fmp"]["api_key"]
    except Exception:
        st.error("No se encontró la API Key. Por favor revisa tu archivo .streamlit/secrets.toml")
        return None

@st.cache_data(ttl=86400) 
def fetch_stock_data(ticker, api_key, start_date):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
    
    # Usamos adjClose para considerar dividendos y splits
    params = {
        "apikey": api_key, 
        "from": start_date
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "historical" in data:
            df = pd.DataFrame(data["historical"])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Seleccionar 'adjClose'
            df = df[['date', 'adjClose']] 
            
            # Renombrar columna al ticker
            df = df.rename(columns={'adjClose': ticker})
            
            df.set_index('date', inplace=True)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error buscando {ticker}: {e}")
        return pd.DataFrame()

def get_all_data(portfolios, start_date):
    api_key = get_api_key()
    if not api_key:
        return pd.DataFrame()

    all_tickers = list(set([t for tickers in portfolios.values() for t in tickers]))
    master_df = pd.DataFrame()
    
    # Texto de carga en español
    status_text = st.empty()
    status_text.text("Fenrir está cazando datos...")
    
    for ticker in all_tickers:
        df = fetch_stock_data(ticker, api_key, start_date)
        if not df.empty:
            if master_df.empty:
                master_df = df
            else:
                master_df = master_df.join(df, how='outer')
            
    status_text.empty()
    return master_df

def get_stock_returns(master_df, portfolios):
    """Calcula el retorno total % para cada acción individual."""
    # Limpiar datos
    df = master_df.ffill().dropna()
    if df.empty: return {}

    start_prices = df.iloc[0]
    end_prices = df.iloc[-1]
    
    returns_map = {}
    
    for p_name, tickers in portfolios.items():
        if p_name == "Benchmark": continue 
        
        p_data = []
        for ticker in tickers:
            if ticker in df.columns:
                total_ret = ((end_prices[ticker] - start_prices[ticker]) / start_prices[ticker]) * 100
                p_data.append({"Stock": ticker, "Return": total_ret})
        
        # Crear dataframe y ordenar
        p_df = pd.DataFrame(p_data)
        if not p_df.empty:
            p_df = p_df.sort_values("Return", ascending=False)
        returns_map[p_name] = p_df
        
    return returns_map

def calculate_portfolio_performance(master_df, portfolios):
    clean_df = master_df.ffill().dropna()
    if clean_df.empty: return pd.DataFrame()

    # Normalizar a 100
    normalized_df = (clean_df / clean_df.iloc[0]) * 100
    performance_df = pd.DataFrame(index=normalized_df.index)

    for p_name, tickers in portfolios.items():
        valid_tickers = [t for t in tickers if t in normalized_df.columns]
        if valid_tickers:
            performance_df[p_name] = normalized_df[valid_tickers].mean(axis=1)
    
    return performance_df

# --- MAIN APP UI ---

st.title("🐺 Batalla de Portafolios")

# Fetch Data
if get_api_key():
    raw_data = get_all_data(PORTFOLIOS, START_DATE)
    
    if not raw_data.empty:
        # Calcular fecha más reciente
        latest_date = raw_data.index.max().strftime('%Y-%m-%d')
        st.caption(f"Rendimiento desde: **{START_DATE}** | Actualizado: **{latest_date}**")

        # 1. Procesar Datos del Gráfico
        chart_data = calculate_portfolio_performance(raw_data, PORTFOLIOS)
        
        if not chart_data.empty:
            # Métricas
            final_vals = chart_data.iloc[-1]
            start_vals = chart_data.iloc[0]
            total_returns = ((final_vals - start_vals) / start_vals) * 100
            
            # Mostrar Métricas Superiores
            cols = st.columns(len(PORTFOLIOS))
            for i, (col, p_name) in enumerate(zip(cols, PORTFOLIOS.keys())):
                ret = total_returns.get(p_name, 0)
                col.metric(p_name, f"{ret:.1f}%")

            # Gráfico (Más alto para celular)
            st.markdown("---")
            
            # Etiquetas en español
            fig = px.line(chart_data, x=chart_data.index, y=chart_data.columns, 
                          labels={"value": "Valor Normalizado ($)", "date": "Fecha", "variable": "Portafolio"},
                          color_discrete_map={
                              # FIX: Use "Benchmark" (the dictionary key), not "SPY"
                              "Benchmark": "gray",  
                              
                              # Fenrir: A blood orange/red hex code
                              "Fenrir": "#EC5C73",  
                              
                              # ChatGPT: A standard CSS named color
                              "ChatGPT": "mediumseagreen", 
                              
                              # Gemini: A bright cyan hex code to pop against dark mode
                              "Gemini": "#00CCFF"   
                          })
            
            fig.update_layout(
                height=600, 
                legend=dict(orientation="h", y=-0.2, x=0, title=None),
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis_title=None,
                xaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. Tablas Individuales
            st.markdown("### Desglose por Portafolio")
            
            stock_returns = get_stock_returns(raw_data, PORTFOLIOS)
            
            # Columnas
            p_cols = st.columns(3)
            target_portfolios = ["ChatGPT", "Gemini", "Fenrir"]
            
            for i, p_name in enumerate(target_portfolios):
                with p_cols[i]:
                    st.subheader(p_name)
                    if p_name in stock_returns:
                        df = stock_returns[p_name]
                        
                        # Copia para visualización en español
                        df_display = df.copy()
                        df_display.columns = ["Acción", "Rendimiento"] # Renombrar headers
                        
                        # Formato porcentaje
                        df_display["Rendimiento"] = df_display["Rendimiento"].map("{:+.2f}%".format)
                        
                        # Mostrar tabla limpia
                        st.dataframe(
                            df_display, 
                            hide_index=True, 
                            use_container_width=True
                        )
        else:
            st.error("No hay suficientes datos. Intenta con una fecha de inicio más antigua.")
    else:
        st.error("La API no devolvió datos.")
