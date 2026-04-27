"""
Robust Data Loader Module
Uses TwelveData API with Yahoo Finance fallback
Compatible with TradingView Lightweight Charts
"""

import pandas as pd
import yfinance as yf
import streamlit as st
import time
import requests
from datetime import datetime

# TwelveData API Configuration
TWELVEDATA_API_KEY = "8f11110e04b14735ba14feb91b134392"  # Replace with your API key from https://twelvedata.com/
TWELVEDATA_BASE_URL = "https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1min&outputsize=5000&apikey=8f11110e04b14735ba14feb91b134392" 

# Symbol mapping for TwelveData
TWELVEDATA_SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "BTCUSD": "BTC/USD"
}

# Yahoo Finance fallback mapping
YAHOO_MAPPING = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "BTCUSD": "BTC-USD"
}

# Yahoo timeframe limits
TIMEFRAME_PERIOD = {
    "1m": "7d",
    "5m": "30d",
    "15m": "60d",
    "1h": "1y",
    "4h": "2y",
    "1d": "5y"
}

# TwelveData interval mapping
TD_INTERVALS = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day"
}


def get_period(interval):
    return TIMEFRAME_PERIOD.get(interval, "5y")


def fetch_from_twelvedata(symbol, timeframe, outputsize=5000):
    """
    Fetch candlestick data from TwelveData API.
    Returns DataFrame or None if failed.
    """
    td_symbol = TWELVEDATA_SYMBOLS.get(symbol, symbol)
    td_interval = TD_INTERVALS.get(timeframe, "1h")
    
    params = {
        "symbol": td_symbol,
        "interval": td_interval,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_API_KEY,
        "format": "JSON"
    }
    
    print(f"  TwelveData: {td_symbol} @ {td_interval}")
    
    try:
        response = requests.get(TWELVEDATA_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if "code" in data and data["code"] != 200:
            print(f"  TwelveData error: {data.get('message', 'Unknown error')}")
            return None
        
        # Parse the response
        if "values" in data and data["values"]:
            df = pd.DataFrame(data["values"])
            
            # Rename columns to standard format
            column_mapping = {
                "datetime": "Datetime",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close"
            }
            df = df.rename(columns=column_mapping)
            
            # Convert datetime
            df["Datetime"] = pd.to_datetime(df["Datetime"])
            df = df.set_index("Datetime")
            df = df.sort_index()
            
            print(f"  TwelveData returned {len(df)} rows")
            return df
        else:
            print("  TwelveData: No values in response")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"  TwelveData request failed: {e}")
        return None
    except Exception as e:
        print(f"  TwelveData error: {e}")
        return None


def fetch_from_yahoo(symbol, timeframe):
    """
    Fetch candlestick data from Yahoo Finance (fallback).
    Returns DataFrame or None if failed.
    """
    mapped_symbol = YAHOO_MAPPING.get(symbol, symbol)
    period = get_period(timeframe)
    yf_interval = "1h" if timeframe == "4h" else timeframe
    
    print(f"  Yahoo Finance: {mapped_symbol} @ {yf_interval}, period: {period}")
    
    tickers_to_try = [mapped_symbol]
    
    # Add fallbacks
    if mapped_symbol == "GC=F":
        tickers_to_try.extend(["XAUUSD=X", "GLD"])
    elif mapped_symbol == "BTC-USD":
        tickers_to_try.append("BTC-USD")
    elif mapped_symbol == "EURUSD=X":
        tickers_to_try.append("EURUSD")
    
    for try_ticker in tickers_to_try:
        try:
            df = yf.download(
                try_ticker,
                period=period,
                interval=yf_interval,
                progress=False,
                auto_adjust=False
            )
            
            if df is not None and not df.empty:
                print(f"  Yahoo Finance: Downloaded {try_ticker}, {len(df)} rows")
                return df
                
        except Exception as e:
            print(f"  Yahoo Finance: Failed {try_ticker}: {e}")
            continue
    
    return None


def process_dataframe(df, timeframe):
    """
    Process DataFrame to Lightweight Charts format.
    Returns (DataFrame, list of candle dicts).
    """
    if df is None or df.empty:
        return pd.DataFrame(), []
    
    # Handle MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Convert columns to lowercase
    df.columns = [str(c).lower() for c in df.columns]
    
    # Drop NaN rows
    df = df.dropna()
    
    if df.empty:
        return pd.DataFrame(), []
    
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # Resample for 4h timeframe
    if timeframe == "4h":
        df = df.resample("4H").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last"
        }).dropna()
    
    if df.empty:
        return pd.DataFrame(), []
    
    # Sort by datetime
    df = df.sort_index()
    
    # Reset index to work with columns
    df = df.reset_index()
    
    # Identify the date column
    date_col = next((col for col in df.columns if col.lower() in ['datetime', 'date', 'index']), df.columns[0])
    
    df = df.rename(columns={date_col: "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["time"] = df["datetime"].astype("int64") // 10**9
    
    # Ensure OHLC columns are floats
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    # Sort by time ascending
    df = df.sort_values("time")
    
    # Build chart data
    chart_data = df[["time", "open", "high", "low", "close"]].to_dict("records")
    
    return df, chart_data


@st.cache_data(ttl=300)
def fetch_data(symbol, timeframe):
    """
    Fetch candlestick data with TwelveData primary and Yahoo fallback.
    Returns (DataFrame, chart_data) tuple.
    """
    print(f"\n{'='*50}")
    print(f"DATA REQUEST")
    print(f"  Symbol: {symbol}")
    print(f"  Timeframe: {timeframe}")
    print(f"{'='*50}")
    
    # Try TwelveData first
    print("Attempting TwelveData API...")
    df = None
    
    for attempt in range(2):
        df = fetch_from_twelvedata(symbol, timeframe)
        if df is not None and not df.empty:
            print("✓ TwelveData succeeded")
            break
        if attempt < 1:
            print("Retrying TwelveData...")
            time.sleep(1)
    
    # Fallback to Yahoo Finance if TwelveData fails
    if df is None or df.empty:
        print("\nFalling back to Yahoo Finance...")
        df = fetch_from_yahoo(symbol, timeframe)
        
        if df is None or df.empty:
            print("✗ All data sources failed")
            return pd.DataFrame(), []
    
    # Process DataFrame to chart data
    df, chart_data = process_dataframe(df, timeframe)
    
    if not chart_data:
        print("✗ Chart data empty after processing")
        return pd.DataFrame(), []
    
    print(f"✓ Final chart data: {len(chart_data)} candles")
    print(f"  First candle: {chart_data[0]}")
    print(f"  Last candle: {chart_data[-1]}")
    
    return df, chart_data