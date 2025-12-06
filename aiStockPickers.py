import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Portfolio Battle: GPT vs Gemini vs Fenrir", layout="wide")

# define the tickers for each portfolio (10 stocks each)
PORTFOLIOS = {
    "ChatGPT": ["MSFT", "NVDA", "CRM", "ADBE", "ORCL", "IBM", "AMD", "INTC", "CSCO", "NOW"],
    "Gemini": ["GOOGL", "AMZN", "META", "AAPL", "NFLX", "TSM", "AVGO", "QCOM", "TXN", "AMAT"],
    # Fenrir: A more aggressive/wolf-themed mix (Crypto proxies, High Beta)
    "Fenrir": ["TSLA", "COIN", "MSTR", "PLTR", "HOOD", "SQ", "DKNG", "ROKU", "SHOP", "NET"], 
    "Benchmark": ["SPY"]
}

# --- FUNCTIONS ---

def get_api_key():
    """Retrieves API key from Streamlit secrets."""
    try:
        return st.secrets["fmp"]["api_key"]
    except Exception:
        st.error("API Key not found. Please check your .streamlit/secrets.toml file.")
        return None

@st.cache_data(ttl=86400) # Cache data for 24 hours
def fetch_stock_data(ticker, api_key, start_date):
    """
    Fetches historical data for a single ticker from FMP.
    """
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
    params = {
        "apikey": api_key,
        "from": start_date,
        "serietype": "line"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "historical" in data:
            df = pd.DataFrame(data["historical"])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df = df[['date', 'close']]
            df = df.rename(columns={'close': ticker})
            df.set_index('date', inplace=True)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.warning(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()

def get_all_data(portfolios, start_date):
    """
    Iterates through all portfolios and fetches data for all tickers.
    """
    api_key = get_api_key()
    if not api_key:
        return pd.DataFrame()

    all_tickers = []
    for p_name, tickers in portfolios.items():
        all_tickers.extend(tickers)
    
    # Remove duplicates
    all_tickers = list(set(all_tickers))
    
    master_df = pd.DataFrame()
    
    # Create a progress bar
    progress_text = "Fetching market data from FMP..."
    my_bar = st.progress(0, text=progress_text)
    
    total_tickers = len(all_tickers)
    
    for i, ticker in enumerate(all_tickers):
        df = fetch_stock_data(ticker, api_key, start_date)
        if not df.empty:
            if master_df.empty:
                master_df = df
            else:
                master_df = master_df.join(df, how='outer')
        
        # Update progress bar
        my_bar.progress((i + 1) / total_tickers, text=f"Fetching {ticker}...")
            
    my_bar.empty()
    return master_df

def calculate_portfolio_performance(master_df, portfolios):
    """
    Normalizes prices to start at 100 and calculates portfolio averages.
    """
    # Forward fill missing data (for weekends/holidays differences if any) then drop remaining NAs
    clean_df = master_df.ffill().dropna()
    
    if clean_df.empty:
        return pd.DataFrame()

    # Normalize individual stocks to start at 100
    normalized_df = (clean_df / clean_df.iloc[0]) * 100

    performance_df = pd.DataFrame(index=normalized_df.index)

    # Calculate Equal Weighted Portfolio Performance
    for p_name, tickers in portfolios.items():
        # Only select tickers that successfully returned data
        valid_tickers = [t for t in tickers if t in normalized_df.columns]
        if valid_tickers:
            performance_df[p_name] = normalized_df[valid_tickers].mean(axis=1)
    
    return performance_df

# --- MAIN APP UI ---

st.title("🐺 Portfolio Evolution: The Battle")
st.markdown("Comparing **ChatGPT**, **Gemini**, and **Fenrir** vs the **S&P 500**.")

col1, col2 = st.columns(2)
with col1:
    # Default to 1 year ago
    default_start = datetime.now() - timedelta(days=365)
    start_date = st.date_input("Start Date", default_start)

# Fetch Data
st.divider()

# Only fetch if we have a valid key
if get_api_key():
    raw_data = get_all_data(PORTFOLIOS, start_date.strftime("%Y-%m-%d"))
    
    if not raw_data.empty:
        # Process Data
        chart_data = calculate_portfolio_performance(raw_data, PORTFOLIOS)
        
        if not chart_data.empty:
            # Calculate total return for the period
            final_vals = chart_data.iloc[-1]
            start_vals = chart_data.iloc[0]
            total_returns = ((final_vals - start_vals) / start_vals) * 100
            
            # Display Metrics
            st.subheader("Total Return (%)")
            m_cols = st.columns(len(PORTFOLIOS))
            for i, (col, portfolio_name) in enumerate(zip(m_cols, PORTFOLIOS.keys())):
                ret = total_returns.get(portfolio_name, 0)
                col.metric(label=portfolio_name, value=f"{ret:.2f}%")

            # Plot Chart
            st.subheader("Performance Over Time (Rebased to 100)")
            fig = px.line(chart_data, x=chart_data.index, y=chart_data.columns, 
                          labels={"value": "Normalized Value ($)", "date": "Date", "variable": "Portfolio"},
                          color_discrete_map={
                              "SPY": "gray",
                              "Fenrir": "red", 
                              "ChatGPT": "green",
                              "Gemini": "blue"
                          })
            st.plotly_chart(fig, use_container_width=True)
            
            # Show raw data toggle
            with st.expander("See Raw Portfolio Data"):
                st.dataframe(chart_data.sort_index(ascending=False))
        else:
            st.error("Not enough data to generate chart. Try an older start date.")
    else:
        st.error("No data returned from API.")
