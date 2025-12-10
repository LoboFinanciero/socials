import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Batalla de Portafolios", layout="wide")

# 1. FECHA DE INICIO (HARD-CODED)
START_DATE = "2025-12-05"

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
        "GTM",  # Granite Ridge
        "BBWI", # Bath & Body Works
        "SMCI", # Super Micro Computer
        "ALGM"  # Allegro MicroSystems
    ], 
    "SPY": ["SPY"]
}

# Define colors for UI consistency
COLORS = {
    "Fenrir": "#EC5C73",      # Red/Pink
    "ChatGPT": "#3CB371",     # Medium Sea Green
    "Gemini": "#00CCFF",      # Cyan
    "SPY": "#808080"          # Gray
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
            df = df[['date', 'adjClose']] 
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
    df = master_df.ffill().dropna()
    if df.empty: return {}

    start_prices = df.iloc[0]
    end_prices = df.iloc[-1]
    
    returns_map = {}
    
    for p_name, tickers in portfolios.items():
        if p_name == "SPY": continue 
        
        p_data = []
        for ticker in tickers:
            if ticker in df.columns:
                total_ret = ((end_prices[ticker] - start_prices[ticker]) / start_prices[ticker]) * 100
                p_data.append({"Stock": ticker, "Return": total_ret})
        
        p_df = pd.DataFrame(p_data)
        if not p_df.empty:
            p_df = p_df.sort_values("Return", ascending=False)
        returns_map[p_name] = p_df
        
    return returns_map

def calculate_portfolio_performance(master_df, portfolios):
    clean_df = master_df.ffill().dropna()
    if clean_df.empty: return pd.DataFrame()

    normalized_df = (clean_df / clean_df.iloc[0]) * 100
    performance_df = pd.DataFrame(index=normalized_df.index)

    for p_name, tickers in portfolios.items():
        valid_tickers = [t for t in tickers if t in normalized_df.columns]
        if valid_tickers:
            performance_df[p_name] = normalized_df[valid_tickers].mean(axis=1)
    
    return performance_df

# --- MAIN APP UI ---

# CSS INJECTION FOR CUSTOM CARDS
st.markdown("""
<style>
    .metric-card {
        background-color: #262730;
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 8px; /* Less space between cards */
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        color: white;
        border: 1px solid #333;
        
        /* THE MAGIC SAUCE: Horizontal Layout */
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Column 1: Rank/Icon */
    .card-col-left {
        width: 15%;
        font-size: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Column 2: Name & % */
    .card-col-mid {
        flex-grow: 1;
        padding-left: 15px;
        text-align: left;
    }
    .mid-name {
        font-size: 14px;
        font-weight: bold;
        color: #ddd;
        margin-bottom: 2px;
    }
    .mid-value {
        font-size: 20px;
        font-weight: bold;
        letter-spacing: 0.5px;
    }
    
    /* Column 3: Delta */
    .card-col-right {
        text-align: right;
        font-size: 13px;
        font-weight: 500;
        min-width: 80px; /* Ensure space for the text */
    }
</style>
""", unsafe_allow_html=True)

st.title("🐺 Batalla de Portafolios")

# Fetch Data
if get_api_key():
    raw_data = get_all_data(PORTFOLIOS, START_DATE)
    
    if not raw_data.empty:
        latest_date = raw_data.index.max().strftime('%Y-%m-%d')
        st.caption(f"Rendimiento desde: **{START_DATE}** | Hasta: **{latest_date}**")

        chart_data = calculate_portfolio_performance(raw_data, PORTFOLIOS)
        
        if not chart_data.empty:
            # Métricas
            final_vals = chart_data.iloc[-1]
            start_vals = chart_data.iloc[0]
            total_returns = ((final_vals - start_vals) / start_vals) * 100

            # --- SORTING LOGIC ---
            sorted_returns = total_returns.sort_values(ascending=False)
            winner_val = sorted_returns.iloc[0]

            # --- CUSTOM CARD DISPLAY (ROW FORMAT) ---
            
            # Get the total count to find who is last
            total_portfolios = len(sorted_returns)
            
            for index, (p_name, ret) in enumerate(sorted_returns.items()):
                # Determine styling
                border_color = COLORS.get(p_name, "#ffffff")
                
                # --- ICON LOGIC ---
                if index == 0:
                    icon = "🏆" 
                    delta_text = "👑 Líder"
                    delta_sub = "" # No subtitle for the winner
                    delta_color = "#4CAF50" # Green
                else:
                    # Check for last place
                    if index == total_portfolios - 1:
                        icon = "🤡" # Clown for last place
                    elif index == 1: 
                        icon = "🥈"
                    elif index == 2: 
                        icon = "🥉"
                    else: 
                        icon = f"#{index+1}"
                    
                    gap = ret - winner_val
                    delta_text = f"{gap:.1f}%" 
                    delta_sub = "vs Líder" # The subtitle you requested
                    delta_color = "#FF4B4B" # Red
                
                # Custom HTML Row-Card
                st.markdown(f"""
                <div class="metric-card" style="border-left: 5px solid {border_color};">
                    <div class="card-col-left">
                        {icon}
                    </div>
                    <div class="card-col-mid">
                        <div class="mid-name">{p_name}</div>
                        <div class="mid-value">{ret:.1f}%</div>
                    </div>
                    <div class="card-col-right" style="color: {delta_color};">
                        <div>{delta_text}</div>
                        <div style="font-size: 9px; opacity: 0.7; color: #ccc;">{delta_sub}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # --- PLOTLY CHART ---
            st.markdown("---")
            st.subheader("Historial de Rendimiento") # Added Title
            
            fig = px.line(chart_data, x=chart_data.index, y=chart_data.columns, 
                          labels={"value": "Valor Normalizado", "date": "Fecha", "variable": "Portafolio"},
                          color_discrete_map=COLORS)
            
            fig.update_layout(
                height=500, # Slightly shorter for mobile scannability
                legend=dict(
                    orientation="h", 
                    y=-0.2, 
                    x=0, 
                    title=None,
                    font=dict(size=10) # Smaller font for mobile
                ),
                margin=dict(l=10, r=10, t=20, b=20), # Tight margins for mobile
                yaxis_title=None,
                xaxis_title=None,
                hovermode="x unified", # Easier to read on touch
                dragmode=False,   # Disables panning (dragging) the chart
                modebar=dict(orientation='v') # Optional: keeps modebar vertical if visible
            )
            
            # KEY UPDATE: config settings for mobile UX
            st.plotly_chart(
                fig, 
                use_container_width=True,
                config={
                    'scrollZoom': False,       # PREVENTS ACCIDENTAL ZOOMING ON SCROLL
                    'displayModeBar': False,   # Hides the toolbar to keep it clean
                    'staticPlot': False
                }
            )
            
            # 2. Tablas Individuales
            st.markdown("### Desglose por Portafolio")
            
            stock_returns = get_stock_returns(raw_data, PORTFOLIOS)
            
            p_cols = st.columns(3)
            target_portfolios = ["ChatGPT", "Gemini", "Fenrir"]
            
            for i, p_name in enumerate(target_portfolios):
                with p_cols[i]:
                    # Use markdown with color for the header
                    st.markdown(f"<h4 style='color: {COLORS.get(p_name, 'white')}; border-bottom: 2px solid {COLORS.get(p_name, 'white')}'>{p_name}</h4>", unsafe_allow_html=True)
                    
                    if p_name in stock_returns:
                        df = stock_returns[p_name]
                        df_display = df.copy()
                        df_display.columns = ["Acción", "Retorno"]
                        df_display["Retorno"] = df_display["Retorno"].map("{:+.2f}%".format)
                        
                        st.dataframe(
                            df_display, 
                            hide_index=True, 
                            use_container_width=True
                        )
        else:
            st.error("No hay suficientes datos. Intenta con una fecha de inicio más antigua.")
    else:
        st.error("La API no devolvió datos.")
