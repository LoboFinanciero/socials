import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Portfolio Battle", layout="wide")

# 1. HARD-CODED START DATE
# Change this string to whatever start date you want (YYYY-MM-DD)
START_DATE = "2024-01-01"

PORTFOLIOS = {
    "ChatGPT": ["MSFT", "NVDA", "CRM", "ADBE", "ORCL", "IBM", "AMD", "INTC", "CSCO", "NOW"],
    "Gemini": ["GOOGL", "AMZN", "META", "AAPL", "NFLX", "TSM", "AVGO", "QCOM", "TXN", "AMAT"],
    "Fenrir": ["TSLA", "COIN", "MSTR", "PLTR", "HOOD", "SQ", "DKNG", "ROKU", "SHOP", "NET"], 
    "Benchmark": ["SPY"]
}

# --- FUNCTIONS ---

def get_api_key():
    try:
        return st.secrets["fmp"]["api_key"]
    except Exception:
        st.error("API Key not found. Please check your .streamlit/secrets.toml file.")
        return None

@st.cache_data(ttl=86400) 
def fetch_stock_data(ticker, api_key, start_date):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
    
    # REMOVE "serietype": "line" so we get the full data (including adjClose)
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
            
            # CHANGE: Select 'adjClose' instead of 'close'
            df = df[['date', 'adjClose']] 
            
            # Rename it to the ticker name so the join works later
            df = df.rename(columns={'adjClose': ticker})
            
            df.set_index('date', inplace=True)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        # It's often good to print the error to the terminal logs for debugging
        print(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()

def get_all_data(portfolios, start_date):
    api_key = get_api_key()
    if not api_key:
        return pd.DataFrame()

    all_tickers = list(set([t for tickers in portfolios.values() for t in tickers]))
    master_df = pd.DataFrame()
    
    # Simple progress text without the bar to save mobile space
    status_text = st.empty()
    status_text.text("🐺 Fenrir is hunting for data...")
    
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
    """Calculates total return % for every individual stock."""
    # clean data
    df = master_df.ffill().dropna()
    if df.empty: return {}

    start_prices = df.iloc[0]
    end_prices = df.iloc[-1]
    
    returns_map = {}
    
    for p_name, tickers in portfolios.items():
        if p_name == "Benchmark": continue # Skip SPY for the individual tables
        
        p_data = []
        for ticker in tickers:
            if ticker in df.columns:
                total_ret = ((end_prices[ticker] - start_prices[ticker]) / start_prices[ticker]) * 100
                p_data.append({"Stock": ticker, "Return": total_ret})
        
        # Create dataframe and sort by highest return
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

st.title("🐺 Portfolio Battle")
st.caption(f"Tracking performance from: {START_DATE}")

# Fetch Data
if get_api_key():
    raw_data = get_all_data(PORTFOLIOS, START_DATE)
    
    if not raw_data.empty:
        # --- NEW CODE START ---
        # Get the latest date available in the dataset
        latest_date = raw_data.index.max().strftime('%Y-%m-%d')
        
        # Update the caption to show the full range
        st.caption(f"📅 Tracking performance from: **{START_DATE}** | Latest data: **{latest_date}**")
        # --- NEW CODE END ---

        # 1. Process Chart Data
        chart_data = calculate_portfolio_performance(raw_data, PORTFOLIOS)
        
        if not chart_data.empty:
            # Metrics
            final_vals = chart_data.iloc[-1]
            start_vals = chart_data.iloc[0]
            total_returns = ((final_vals - start_vals) / start_vals) * 100
            
            # Display Top Level Metrics
            cols = st.columns(len(PORTFOLIOS))
            for i, (col, p_name) in enumerate(zip(cols, PORTFOLIOS.keys())):
                ret = total_returns.get(p_name, 0)
                col.metric(p_name, f"{ret:.1f}%")

            # Chart (Taller for Mobile)
            st.markdown("---")
            fig = px.line(chart_data, x=chart_data.index, y=chart_data.columns, 
                          color_discrete_map={
                              "SPY": "gray", "Fenrir": "red", 
                              "ChatGPT": "green", "Gemini": "blue"
                          })
            
            # Mobile Optimization: Increase height, move legend to bottom to save width
            fig.update_layout(
                height=600, 
                legend=dict(orientation="h", y=-0.2, x=0, title=None),
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis_title=None,
                xaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. Individual Stock Tables
            st.markdown("### 📊 Portfolio Breakdown")
            
            stock_returns = get_stock_returns(raw_data, PORTFOLIOS)
            
            # Create 3 columns for desktop (will stack on mobile)
            p_cols = st.columns(3)
            
            # Iterate through our 3 main portfolios
            target_portfolios = ["ChatGPT", "Gemini", "Fenrir"]
            
            for i, p_name in enumerate(target_portfolios):
                with p_cols[i]:
                    st.subheader(p_name)
                    if p_name in stock_returns:
                        df = stock_returns[p_name]
                        # Format the Return column as a percentage string
                        df_display = df.copy()
                        df_display["Return"] = df_display["Return"].map("{:+.2f}%".format)
                        
                        # Display clean table
                        st.dataframe(
                            df_display, 
                            hide_index=True, 
                            use_container_width=True
                        )
        else:
            st.error("Not enough data overlap. Try a more recent start date.")
    else:
        st.error("No data returned from API.")
