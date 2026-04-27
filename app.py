import streamlit as st
import pandas as pd
import numpy as np
import json
import streamlit.components.v1 as components
from datetime import datetime

from data_loader import fetch_data
from session_manager import initialize_session_state
from replay_engine import ReplayEngine
from trade_simulator import TradeSimulator
from performance_metrics import PerformanceMetrics
from indicators import calculate_ema_200_and_signals

st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        .main { background-color: #0e1117; }
        h1, h2, h3 { color: #fafafa; }
        .stMetric { background-color: #1e2130; padding: 15px; border-radius: 5px; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden}
        header {visibility: hidden}
    </style>
""", unsafe_allow_html=True)

initialize_session_state()

def render_lightweight_chart(df, chart_data, show_ema, signals, symbol, timeframe, is_playing=False):
    df_clean = df.replace({np.nan: None})
    
    # Build props for markers
    props = {
        'symbol': symbol,
        'timeframe': timeframe,
        'is_playing': is_playing,
        'ema20': [{'time': row['time'], 'value': row['ema_200']} for idx, row in df_clean.iterrows() if row['ema_200'] is not None] if show_ema else None,
    }

    markers = []
    for s in signals:
        markers.append({
            'time': int(s['timestamp']),
            'position': 'belowBar' if s['type'] == 'buy' else 'aboveBar',
            'color': '#26a69a' if s['type'] == 'buy' else '#ef5350',
            'shape': 'arrowUp' if s['type'] == 'buy' else 'arrowDown',
            'text': 'Buy' if s['type'] == 'buy' else 'Sell'
        })
    props['markers'] = markers

    with open("chart_component.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    html = html_template.replace(
        "**CANDLE_DATA**",
        json.dumps(chart_data)
    )
    
    print("Injected candles:", len(chart_data))

    components.html(html, height=600)

def main():
    if st.session_state.active_session is None:
        st.title("TradersCasa Web Platform")
        with st.form("new_session_form"):
            st.subheader("Create New Session")
            name = st.text_input("Session Name")
            balance = st.number_input("Starting Balance (USD)", value=1000)
            pair = st.selectbox("Select Asset", ["XAUUSD", "EURUSD", "BTCUSD"])
            timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])
            start_date = st.date_input("Start Date")
            desc = st.text_area("Description")
            
            if st.form_submit_button("Start Session"):
                session = st.session_state.sm.create_session(name, balance, pair, str(start_date), timeframe, desc)
                st.session_state.active_session = session
                st.session_state.trades = []
                st.rerun()
        return

    sess = st.session_state.active_session
    
    # Load Historical Data
    df, chart_data = fetch_data(sess['pair'], sess['timeframe'])
    
    # Debug: Print candle count
    print("="*60)
    print("Candles received from fetch_data:", len(chart_data))
    if chart_data:
        print("First candle:", chart_data[0])
        print("Last candle:", chart_data[-1])
    else:
        print("WARNING: chart_data is empty!")
    print("="*60)
    
    # Check for empty data and show warning instead of blank chart
    if df.empty or not chart_data:
        st.warning("⚠ No candle data available. Please try a different symbol or timeframe.")
        st.info(f"Selected: {sess['pair']} on {sess['timeframe']} timeframe")
        if st.button("Exit Session"):
            st.session_state.active_session = None
            st.rerun()
        return

    # Find start index based on Date
    if st.session_state.replay_index == 0:
        try:
            # Convert session start date to UNIX timestamp
            start_date_ts = int(pd.Timestamp(sess['start_date']).tz_localize('UTC').timestamp())
            # Find the index where timestamp >= start_date
            if 'time' in df.columns:
                start_idx = df[df['time'] >= start_date_ts].index[0] if len(df[df['time'] >= start_date_ts]) > 0 else len(df) - 1
            else:
                start_idx = 0
            st.session_state.replay_index = max(100, min(start_idx, len(df)-1))
        except (KeyError, IndexError):
            st.session_state.replay_index = max(100, len(df) // 2)

    max_index = len(df)
    
    # Top Toolbar
    t_col1, t_col2, t_col3, t_col4, t_col5, t_col6, t_col7 = st.columns([1,1,1,1,1,2,2])
    show_ema = t_col1.toggle("EMA 200")
    t_col2.button("⏪ Rewind", on_click=ReplayEngine.rewind)
    t_col3.button("▶ Play", on_click=ReplayEngine.play, args=(max_index,))
    t_col4.button("⏸ Pause", on_click=ReplayEngine.pause)
    t_col5.button("⏭ Step", on_click=ReplayEngine.step_forward, args=(max_index,))
    
    st.session_state.replay_speed = t_col6.selectbox("Speed", ["1x", "2x", "4x", "8x"], index=0, label_visibility="collapsed")
    
    if t_col7.button("❌ Exit Session"):
        st.session_state.active_session = None
        st.session_state.is_playing = False
        st.rerun()

    # Slice logic
    df_sliced = df.iloc[:st.session_state.replay_index]
    chart_data_sliced = chart_data[:st.session_state.replay_index]
    
    current_price = df_sliced['close'].iloc[-1] if not df_sliced.empty else 0
    current_time = pd.to_datetime(df_sliced['time'].iloc[-1], unit='s').strftime('%Y-%m-%d %H:%M:%S') if not df_sliced.empty and 'time' in df_sliced.columns else None

    # Calculate Indicators
    df_ind, signals = calculate_ema_200_and_signals(df_sliced) if show_ema else (df_sliced, [])

    # Trade Simulator Panel (Top right or floating, keeping it inline for simplicity)
    with st.expander("💼 Trade Simulator", expanded=True):
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        if col_b1.button("🟢 BUY Market", use_container_width=True):
            TradeSimulator.open_position("LONG", current_price, current_time)
        if col_b2.button("🔴 SELL Market", use_container_width=True):
            TradeSimulator.open_position("SHORT", current_price, current_time)
            
        open_trades = [t for t in st.session_state.trades if t['status'] == 'OPEN']
        if open_trades:
            trade_to_close = col_b3.selectbox("Select Trade to Close", [t['id'] for t in open_trades], label_visibility="collapsed")
            if col_b4.button("Close Trade", use_container_width=True):
                TradeSimulator.close_position(trade_to_close, current_price, current_time)

    # Chart View
    render_lightweight_chart(df_ind, chart_data_sliced, show_ema, signals, sess['pair'], sess['timeframe'], st.session_state.is_playing)

    # Bottom Panel: History & Metrics
    st.markdown("---")
    open_pnl = TradeSimulator.get_open_pnl(current_price)
    metrics = PerformanceMetrics.calculate(st.session_state.trades, sess['balance'])
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Current Balance", f"${sess['balance'] + metrics['total_profit'] + open_pnl:,.2f}")
    m2.metric("Open PnL", f"${open_pnl:,.2f}")
    m3.metric("Closed Profit", f"${metrics['total_profit']:,.2f}")
    m4.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
    m5.metric("Total Trades", metrics['total_trades'])
    m6.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")

    st.subheader("Trade History")
    if st.session_state.trades:
        tdf = pd.DataFrame(st.session_state.trades)
        st.dataframe(tdf[['id', 'direction', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'pnl', 'status']], use_container_width=True)

    # Execute Replay tick if playing
    ReplayEngine.run_loop(max_index)

if __name__ == "__main__":
    main()            