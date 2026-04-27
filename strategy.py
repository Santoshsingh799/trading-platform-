"""
Strategy Module
"""
import pandas as pd
import numpy as np

def calculate_indicators(df, show_ema20=True, show_ema50=True):
    if show_ema20:
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    if show_ema50:
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    return df

def generate_signals(df):
    signals = []
    if 'ema_20' not in df.columns or 'ema_50' not in df.columns:
        return signals
        
    for i in range(1, len(df)):
        if pd.isna(df['ema_20'].iloc[i]) or pd.isna(df['ema_50'].iloc[i]):
            continue
            
        prev_ema_20 = df['ema_20'].iloc[i-1]
        prev_ema_50 = df['ema_50'].iloc[i-1]
        curr_ema_20 = df['ema_20'].iloc[i]
        curr_ema_50 = df['ema_50'].iloc[i]
        
        if prev_ema_20 <= prev_ema_50 and curr_ema_20 > curr_ema_50:
            signals.append({'timestamp': df.index[i], 'type': 'buy', 'price': df['close'].iloc[i]})
        elif prev_ema_20 >= prev_ema_50 and curr_ema_20 < curr_ema_50:
            signals.append({'timestamp': df.index[i], 'type': 'sell', 'price': df['close'].iloc[i]})
            
    return signals