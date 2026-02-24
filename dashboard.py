import streamlit as st
import pykx as kx
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import os

# Page Configuration
st.set_page_config(page_title="KDB+ Crypto Engine", layout="wide")
st.title("⚡ Real-Time KDB+ Crypto Dashboard")

# 1. Connect to KDB+ CEP Engine
@st.cache_resource
def get_connection():
    try:
        # Force IPv4 connection to KDB+
        cep_host = os.getenv('CEP_HOST', '127.0.0.1')
        print(f"DEBUG: Dashboard attempting to connect to: {cep_host}:5012")
        return kx.SyncQConnection(host=cep_host, port=5012)
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
if 'ohlc_data' not in st.session_state:
    st.session_state.ohlc_data = pd.DataFrame()

def fetch_data(last_time=None):
    if not q:
        return pd.DataFrame()
    
    try:
        if last_time is None:
            # Full load (initial)
            res = q("0!ohlc")
        else:
            # Incremental load
            res = q("{select from ohlc where time >= x}", last_time)

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
    # Check for new day to handle potential KDB+ midnight reset
    current_midnight = pd.Timestamp.now().normalize()
    if 'last_midnight' not in st.session_state:
        st.session_state.last_midnight = current_midnight

    if current_midnight > st.session_state.last_midnight:
        st.session_state.ohlc_data = pd.DataFrame()
        st.session_state.last_midnight = current_midnight

    # Determine last fetched time
    last_time = None
    if not st.session_state.ohlc_data.empty:
        last_time = st.session_state.ohlc_data['time'].max()

    # Fetch data (incremental or full)
    new_df = fetch_data(last_time)

    # Update session state
    if not new_df.empty:
        if st.session_state.ohlc_data.empty:
            st.session_state.ohlc_data = new_df
        else:
            # Concatenate and sort
            st.session_state.ohlc_data = pd.concat([st.session_state.ohlc_data, new_df], ignore_index=True)
            st.session_state.ohlc_data = st.session_state.ohlc_data.sort_values(by='time').drop_duplicates(subset=['time', 'sym'], keep='last')

    # Use the full dataset for display
    df = st.session_state.ohlc_data

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
            
            # Add a unique key based on time to prevent ID collisions during live updates
            unique_key = f"chart_{time.time()}"
            st.plotly_chart(fig, width='stretch', key=unique_key)
            
            # Data Table (Optional)
            with st.expander("Raw Data (OHLC Table)"):
                st.dataframe(df.sort_values(by='time', ascending=False).head(10))
        else:
            st.info("Waiting for data... Ensure Tickerplant and Feed are running.")
            
    if not auto_refresh:
        break
    
    # Sleep to prevent rapid-fire looping
    time.sleep(5)