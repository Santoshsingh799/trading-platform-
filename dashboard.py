"""
Trading Dashboard
Main Streamlit dashboard for the trading platform.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from cache import MultiTimeframeCache, get_cache
from data_loader import DataLoader, get_data_loader
from indicators import IndicatorEngine
from metrics import PerformanceCalculator, calculate_sharpe, calculate_max_drawdown
from strategies import StrategyManager, create_strategy
from trade_log import TradeLogExporter, export_trades_to_csv


# Page configuration
st.set_page_config(
    page_title="Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    .metric-label {
        font-size: 14px;
        color: #888;
    }
    .positive { color: #4caf50; }
    .negative { color: #f44336; }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# Session state initialization
if 'data_loader' not in st.session_state:
    st.session_state.data_loader = get_data_loader()

if 'cache' not in st.session_state:
    st.session_state.cache = get_cache()

if 'strategy_manager' not in st.session_state:
    st.session_state.strategy_manager = StrategyManager()

if 'indicator_engine' not in st.session_state:
    st.session_state.indicator_engine = IndicatorEngine()

if 'trade_log' not in st.session_state:
    st.session_state.trade_log = TradeLogExporter()

if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False


def load_data(
    symbol: str,
    timeframe: str = '1d',
    period: str = '1y'
) -> pd.DataFrame:
    """Load data with caching."""
    return st.session_state.data_loader.load(symbol, timeframe, period=period)


def calculate_indicators(data: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
    """Calculate indicators on data."""
    engine = IndicatorEngine()
    
    for ind in indicators:
        if ind == 'sma':
            engine.add_indicator('sma_20', 'sma', {'period': 20})
            engine.add_indicator('sma_50', 'sma', {'period': 50})
            engine.add_indicator('sma_200', 'sma', {'period': 200})
        elif ind == 'ema':
            engine.add_indicator('ema_12', 'ema', {'period': 12})
            engine.add_indicator('ema_26', 'ema', {'period': 26})
        elif ind == 'rsi':
            engine.add_indicator('rsi', 'rsi', {'period': 14})
        elif ind == 'macd':
            engine.add_indicator('macd', 'macd', {})
        elif ind == 'bollinger':
            engine.add_indicator('bb', 'bollinger', {'period': 20, 'std_dev': 2})
        elif ind == 'atr':
            engine.add_indicator('atr', 'atr', {'period': 14})
        elif ind == 'stochastic':
            engine.add_indicator('stoch', 'stochastic', {})
        elif ind == 'vwap':
            engine.add_indicator('vwap', 'vwap', {})
    
    return engine.calculate(data)


def run_strategies(
    data: pd.DataFrame,
    symbol: str,
    strategy_types: List[str]
) -> Dict[str, List]:
    """Run multiple strategies on data."""
    manager = StrategyManager()
    
    for i, strat_type in enumerate(strategy_types):
        manager.add_strategy(f'strategy_{i}', strat_type, {'symbol': symbol})
    
    return manager.run_all(data, symbol)


def calculate_performance_metrics(
    data: pd.DataFrame,
    signals: List
) -> Dict[str, float]:
    """Calculate performance metrics from signals."""
    if not signals:
        return {
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_return': 0,
            'win_rate': 0
        }
    
    # Create equity curve from signals
    equity = pd.Series([10000], index=[data.index[0]])
    
    for signal in signals:
        if signal.signal_type.value == 1:  # Buy
            equity = pd.concat([equity, pd.Series([equity.iloc[-1] * 1.01], index=[signal.timestamp])])
        elif signal.signal_type.value == -1:  # Sell
            equity = pd.concat([equity, pd.Series([equity.iloc[-1] * 0.99], index=[signal.timestamp])])
    
    if len(equity) > 1:
        returns = equity.pct_change().dropna()
        sharpe = calculate_sharpe(returns)
        max_dd = calculate_max_drawdown(equity)
        total_return = ((equity.iloc[-1] / equity.iloc[0]) - 1) * 100
    else:
        sharpe = 0
        max_dd = 0
        total_return = 0
    
    return {
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'total_return': total_return,
        'win_rate': 50 if signals else 0
    }


def plot_candlestick(
    data: pd.DataFrame,
    indicators: Optional[pd.DataFrame] = None,
    signals: Optional[List] = None
) -> go.Figure:
    """Create candlestick chart."""
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Price'
    ))
    
    # Add indicators
    if indicators is not None:
        for col in indicators.columns:
            if 'sma' in col.lower() or 'ema' in col.lower():
                fig.add_trace(go.Scatter(
                    x=indicators.index,
                    y=indicators[col],
                    mode='lines',
                    name=col,
                    line=dict(width=1)
                ))
            elif 'bb_upper' in col:
                fig.add_trace(go.Scatter(
                    x=indicators.index,
                    y=indicators[col],
                    mode='lines',
                    name='BB Upper',
                    line=dict(color='rgba(255, 99, 132, 0.5)', width=1),
                    showlegend=False
                ))
            elif 'bb_lower' in col:
                fig.add_trace(go.Scatter(
                    x=indicators.index,
                    y=indicators[col],
                    mode='lines',
                    name='BB Lower',
                    line=dict(color='rgba(255, 99, 132, 0.5)', width=1),
                    fill='tonexty',
                    fillcolor='rgba(255, 99, 132, 0.1)',
                    showlegend=False
                ))
    
    # Add signals
    if signals:
        buy_signals = [s for s in signals if s.signal_type.value == 1]
        sell_signals = [s for s in signals if s.signal_type.value == -1]
        
        if buy_signals:
            fig.add_trace(go.Scatter(
                x=[s.timestamp for s in buy_signals],
                y=[s.price for s in buy_signals],
                mode='markers',
                name='Buy Signal',
                marker=dict(symbol='triangle-up', size=12, color='green')
            ))
        
        if sell_signals:
            fig.add_trace(go.Scatter(
                x=[s.timestamp for s in sell_signals],
                y=[s.price for s in sell_signals],
                mode='markers',
                name='Sell Signal',
                marker=dict(symbol='triangle-down', size=12, color='red')
            ))
    
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=500,
        template='plotly_dark',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


def plot_metrics_comparison(metrics_list: List[Dict]) -> go.Figure:
    """Create metrics comparison chart."""
    fig = go.Figure()
    
    strategies = [m.get('strategy', f'Strategy {i}') for i, m in enumerate(metrics_list)]
    
    # Sharpe ratio
    fig.add_trace(go.Bar(
        x=strategies,
        y=[m.get('sharpe_ratio', 0) for m in metrics_list],
        name='Sharpe Ratio',
        marker_color='#4caf50'
    ))
    
    # Max drawdown
    fig.add_trace(go.Bar(
        x=strategies,
        y=[abs(m.get('max_drawdown', 0)) for m in metrics_list],
        name='Max Drawdown %',
        marker_color='#f44336'
    ))
    
    # Total return
    fig.add_trace(go.Bar(
        x=strategies,
        y=[m.get('total_return', 0) for m in metrics_list],
        name='Total Return %',
        marker_color='#2196f3'
    ))
    
    fig.update_layout(
        barmode='group',
        template='plotly_dark',
        height=400
    )
    
    return fig


def main():
    """Main dashboard function."""
    
    # Sidebar
    st.sidebar.title("⚡ Trading Dashboard")
    
    # Symbol selection
    symbol = st.sidebar.text_input("Symbol", value="AAPL").upper()
    
    # Timeframe selection
    timeframe = st.sidebar.selectbox(
        "Timeframe",
        ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'],
        index=5
    )
    
    # Period selection
    period = st.sidebar.selectbox(
        "Period",
        ['5d', '1mo', '3mo', '6mo', '1y', '2y', '5y'],
        index=4
    )
    
    # Auto refresh toggle
    st.sidebar.markdown("---")
    st.sidebar.subheader("Real-time Settings")
    auto_refresh = st.sidebar.checkbox("Enable Auto Refresh", value=False)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 60, 30)
    
    if auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, key="data_refresh")
    
    # Indicator selection
    st.sidebar.markdown("---")
    st.sidebar.subheader("Indicators")
    selected_indicators = st.sidebar.multiselect(
        "Select Indicators",
        ['sma', 'ema', 'rsi', 'macd', 'bollinger', 'atr', 'stochastic', 'vwap'],
        default=['sma', 'rsi']
    )
    
    # Strategy selection
    st.sidebar.markdown("---")
    st.sidebar.subheader("Strategies")
    selected_strategies = st.sidebar.multiselect(
        "Select Strategies",
        ['sma_crossover', 'rsi', 'macd', 'bollinger_bounce'],
        default=['sma_crossover']
    )
    
    # Main content
    st.title(f"📈 {symbol} Trading Dashboard")
    
    # Load data
    with st.spinner("Loading data..."):
        data = load_data(symbol, timeframe, period)
    
    if data.empty:
        st.error(f"No data available for {symbol}")
        return
    
    # Calculate indicators
    if selected_indicators:
        data_with_indicators = calculate_indicators(data.copy(), selected_indicators)
    else:
        data_with_indicators = data.copy()
    
    # Run strategies
    if selected_strategies:
        strategy_results = run_strategies(data, symbol, selected_strategies)
    else:
        strategy_results = {}
    
    # Tab layout
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Chart", 
        "📈 Performance", 
        "⚔️ Strategy Comparison",
        "📋 Trade Log",
        "⚙️ Settings"
    ])
    
    # Tab 1: Chart
    with tab1:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Main chart
            signals = []
            for strat_signals in strategy_results.values():
                signals.extend(strat_signals)
            
            fig = plot_candlestick(data, data_with_indicators, signals)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Quick Stats")
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            
            change = latest['close'] - prev['close']
            change_pct = (change / prev['close']) * 100
            
            st.metric("Price", f"${latest['close']:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
            st.metric("Volume", f"{latest['volume']:,.0f}")
            st.metric("High", f"${latest['high']:.2f}")
            st.metric("Low", f"${latest['low']:.2f}")
    
    # Tab 2: Performance
    with tab2:
        st.subheader("Performance Metrics")
        
        # Calculate metrics for each strategy
        metrics_data = []
        
        for strat_name, signals in strategy_results.items():
            metrics = calculate_performance_metrics(data, signals)
            metrics['strategy'] = strat_name
            metrics_data.append(metrics)
        
        if metrics_data:
            # Display metrics
            cols = st.columns(4)
            
            for i, metrics in enumerate(metrics_data):
                with cols[i % 4]:
                    st.markdown(f"**{metrics['strategy']}**")
                    st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
                    st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
                    st.metric("Total Return", f"{metrics['total_return']:.2f}%")
                    st.metric("Win Rate", f"{metrics['win_rate']:.1f}%")
                    st.markdown("---")
        else:
            st.info("Select strategies to view performance metrics")
    
    # Tab 3: Strategy Comparison
    with tab3:
        st.subheader("Strategy Comparison")
        
        if len(metrics_data) > 1:
            # Comparison chart
            fig = plot_metrics_comparison(metrics_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Comparison table
            st.subheader("Metrics Comparison Table")
            df = pd.DataFrame(metrics_data)
            st.dataframe(df, use_container_width=True)
        elif len(metrics_data) == 1:
            st.info("Add more strategies to compare")
        else:
            st.info("Select at least one strategy to view comparison")
    
    # Tab 4: Trade Log
    with tab4:
        st.subheader("Trade Log")
        
        # Generate sample trade log from signals
        if strategy_results:
            all_signals = []
            for signals in strategy_results.values():
                all_signals.extend(signals)
            
            # Add to trade log
            for signal in all_signals:
                st.session_state.trade_log.add_entry(
                    timestamp=signal.timestamp,
                    symbol=signal.symbol,
                    action=signal.signal_type.name,
                    quantity=100,
                    price=signal.price,
                    strategy=signal.strategy
                )
            
            # Display trade log
            trade_df = st.session_state.trade_log.to_dataframe()
            if not trade_df.empty:
                st.dataframe(trade_df, use_container_width=True)
                
                # Export button
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Export to CSV"):
                        filepath = f"trade_log_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        st.session_state.trade_log.to_csv(filepath)
                        st.success(f"Exported to {filepath}")
                
                with col2:
                    if st.button("Clear Trade Log"):
                        st.session_state.trade_log.clear()
                        st.success("Trade log cleared")
            else:
                st.info("No trades to display")
        else:
            st.info("Run strategies to generate trade log")
    
    # Tab 5: Settings
    with tab5:
        st.subheader("Cache Settings")
        
        # Cache stats
        cache_stats = st.session_state.cache.get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Cache Hits", cache_stats.get('hits', 0))
        with col2:
            st.metric("Cache Misses", cache_stats.get('misses', 0))
        with col3:
            st.metric("Hit Rate", f"{cache_stats.get('hit_rate', 0):.1%}")
        with col4:
            st.metric("Cache Size", f"{cache_stats.get('size_mb', 0):.1f} MB")
        
        if st.button("Clear Cache"):
            st.session_state.cache.invalidate()
            st.success("Cache cleared")
        
        st.markdown("---")
        st.subheader("Data Loader Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Cache Enabled:** {st.session_state.data_loader.use_cache}")
        with col2:
            if st.button("Refresh Data"):
                st.session_state.cache.invalidate(symbol=symbol)
                st.success(f"Data refreshed for {symbol}")


if __name__ == "__main__":
    main()