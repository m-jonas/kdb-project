import streamlit as st
import pykx as kx
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# Page Configuration
st.set_page_config(page_title="KDB+ Crypto Engine", layout="wide")
st.title("⚡ Real-Time KDB+ Crypto Dashboard")

# 1. Connect to KDB+ CEP Engine
@st.cache_resource
def get_connection():
    try:
        # Force IPv4 connection to KDB+
        return kx.SyncQConnection(host='127.0.0.1', port=5012)
    except Exception as e:
        st.error(f"Failed to connect to CEP Engine: {e}")
        return None

q = get_connection()

# 2. Sidebar Controls
st.sidebar.header("Connection Status")
if q:
    st.sidebar.success("Connected to CEP (:5012)")
else:
    st.sidebar.error("Disconnected")

auto_refresh = st.sidebar.checkbox("Auto-Refresh (5s)", value=True)

# 3. Fetch Data Function
def fetch_data():
    if not q:
        return pd.DataFrame()
    
    try:
        # Query the 'ohlc' table from the CEP engine
        res = q("0!ohlc")
        df = res.pd()
        
        if df.empty:
            return df

        # Convert KDB timespan (Timedelta) to full datetime
        # We take "Midnight Today" and add the timespan duration
        midnight = pd.Timestamp.now().normalize()
        df['datetime'] = midnight + df['time']
        
        return df
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame()

# 4. Main Display Loop
placeholder = st.empty()

while True:
    # Fetch data first
    df = fetch_data()

    # Clear the placeholder to avoid 'DuplicateElementId' and force refresh
    placeholder.empty()

    with placeholder.container():
        if not df.empty:
            # Metrics Row
            last_close = df.iloc[-1]['close']
            last_vwap = df.iloc[-1]['vwap']
            vol_sum = df['volume'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Last Price", f"${last_close:,.2f}")
            c2.metric("VWAP (1m)", f"${last_vwap:,.2f}", delta=f"{last_close-last_vwap:.2f}")
            c3.metric("Total Volume", f"{vol_sum:,.4f}")

            # Candlestick Chart
            fig = go.Figure(data=[go.Candlestick(
                x=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='BTC-USD'
            )])
            
            fig.update_layout(
                title="BTC-USD 1-Minute Bars (Live from KDB+)",
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                template="plotly_dark",
                height=600
            )
            
            # FIX: Add a unique key based on time to prevent ID collisions
            unique_key = f"chart_{time.time()}"
            st.plotly_chart(fig, use_container_width=True, key=unique_key)
            
            # Data Table (Optional)
            with st.expander("Raw Data (OHLC Table)"):
                st.dataframe(df.sort_values(by='time', ascending=False).head(10))
        else:
            st.info("Waiting for data... Ensure Tickerplant and Feed are running.")
            
    if not auto_refresh:
        break
    
    # Sleep to prevent rapid-fire looping
    time.sleep(5)