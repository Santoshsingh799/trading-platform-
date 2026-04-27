import pandas as pd

def calculate_ema_200_and_signals(df):
    """Calculates EMA 200 and generates crossover signals."""
    df = df.copy()
    if df.empty or len(df) < 200:
        df['ema_200'] = None
        return df, []
        
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    signals = []
    for i in range(1, len(df)):
        if pd.isna(df['ema_200'].iloc[i]) or pd.isna(df['ema_200'].iloc[i-1]):
            continue
            
        prev_close = df['close'].iloc[i-1]
        curr_close = df['close'].iloc[i]
        prev_ema = df['ema_200'].iloc[i-1]
        curr_ema = df['ema_200'].iloc[i]
        
        # Bullish Crossover (Buy)
        if prev_close <= prev_ema and curr_close > curr_ema:
            signals.append({'timestamp': df['time'].iloc[i], 'type': 'buy', 'price': curr_close})
            
        # Bearish Crossover (Sell)
        elif prev_close >= prev_ema and curr_close < curr_ema:
            signals.append({'timestamp': df['time'].iloc[i], 'type': 'sell', 'price': curr_close})
            
    return df, signals