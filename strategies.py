"""
Strategy Framework
Modular trading strategy system with multiple strategy support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class SignalType(Enum):
    """Trading signal types."""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class TradeSignal:
    """Represents a trading signal."""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    price: float
    quantity: float = 0
    confidence: float = 1.0
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trade:
    """Represents a completed trade."""
    entry_date: datetime
    exit_date: Optional[datetime]
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0
    pnl_pct: float = 0
    strategy: str = ""
    status: str = "open"  # 'open' or 'closed'


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        self._indicators = {}
        self._signals: List[TradeSignal] = []
        self._positions: Dict[str, float] = {}
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        """Generate trading signals from data."""
        pass
    
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """Return list of required indicator names."""
        pass
    
    def on_bar(self, bar: pd.Series) -> Optional[TradeSignal]:
        """Process a single bar and return signal if any."""
        return None
    
    def reset(self) -> None:
        """Reset strategy state."""
        self._signals.clear()
        self._positions.clear()
    
    @property
    def signals(self) -> List[TradeSignal]:
        return self._signals.copy()
    
    @property
    def positions(self) -> Dict[str, float]:
        return self._positions.copy()


class SMACrossoverStrategy(BaseStrategy):
    """Simple Moving Average Crossover Strategy."""
    
    def get_required_indicators(self) -> List[str]:
        return ['sma_fast', 'sma_slow']
    
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        
        fast_col = self.params.get('fast_column', 'sma_fast')
        slow_col = self.params.get('slow_column', 'sma_slow')
        
        if fast_col not in data.columns or slow_col not in data.columns:
            return signals
        
        for i in range(1, len(data)):
            if pd.isna(data[fast_col].iloc[i]) or pd.isna(data[slow_col].iloc[i]):
                continue
            
            prev_fast = data[fast_col].iloc[i-1]
            prev_slow = data[slow_col].iloc[i-1]
            curr_fast = data[fast_col].iloc[i]
            curr_slow = data[slow_col].iloc[i]
            
            # Golden cross - bullish crossover
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.BUY,
                    price=data['close'].iloc[i],
                    strategy=self.name
                ))
            
            # Death cross - bearish crossover
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.SELL,
                    price=data['close'].iloc[i],
                    strategy=self.name
                ))
        
        self._signals = signals
        return signals


class RSIStrategy(BaseStrategy):
    """RSI Mean Reversion Strategy."""
    
    def get_required_indicators(self) -> List[str]:
        return ['rsi']
    
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        
        rsi_col = self.params.get('rsi_column', 'rsi')
        oversold = self.params.get('oversold', 30)
        overbought = self.params.get('overbought', 70)
        
        if rsi_col not in data.columns:
            return signals
        
        for i in range(1, len(data)):
            if pd.isna(data[rsi_col].iloc[i]):
                continue
            
            rsi = data[rsi_col].iloc[i]
            
            # Oversold - buy signal
            if rsi < oversold:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.BUY,
                    price=data['close'].iloc[i],
                    confidence=(oversold - rsi) / oversold,
                    strategy=self.name
                ))
            
            # Overbought - sell signal
            elif rsi > overbought:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.SELL,
                    price=data['close'].iloc[i],
                    confidence=(rsi - overbought) / (100 - overbought),
                    strategy=self.name
                ))
        
        self._signals = signals
        return signals


class MACDStrategy(BaseStrategy):
    """MACD Momentum Strategy."""
    
    def get_required_indicators(self) -> List[str]:
        return ['macd_macd', 'macd_signal']
    
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        
        macd_col = self.params.get('macd_column', 'macd_macd')
        signal_col = self.params.get('signal_column', 'macd_signal')
        
        if macd_col not in data.columns or signal_col not in data.columns:
            return signals
        
        for i in range(1, len(data)):
            if pd.isna(data[macd_col].iloc[i]) or pd.isna(data[signal_col].iloc[i]):
                continue
            
            prev_macd = data[macd_col].iloc[i-1]
            prev_signal = data[signal_col].iloc[i-1]
            curr_macd = data[macd_col].iloc[i]
            curr_signal = data[signal_col].iloc[i]
            
            # Bullish crossover
            if prev_macd <= prev_signal and curr_macd > curr_signal:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.BUY,
                    price=data['close'].iloc[i],
                    strategy=self.name
                ))
            
            # Bearish crossover
            elif prev_macd >= prev_signal and curr_macd < curr_signal:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.SELL,
                    price=data['close'].iloc[i],
                    strategy=self.name
                ))
        
        self._signals = signals
        return signals


class BollingerBounceStrategy(BaseStrategy):
    """Bollinger Bands Bounce Strategy."""
    
    def get_required_indicators(self) -> List[str]:
        return ['bb_upper', 'bb_lower', 'bb_middle']
    
    def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        signals = []
        
        upper = self.params.get('upper_column', 'bb_upper')
        lower = self.params.get('lower_column', 'bb_lower')
        
        if upper not in data.columns or lower not in data.columns:
            return signals
        
        for i in range(len(data)):
            if pd.isna(data[upper].iloc[i]) or pd.isna(data[lower].iloc[i]):
                continue
            
            close = data['close'].iloc[i]
            
            # Price at lower band - buy signal
            if close <= data[lower].iloc[i]:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.BUY,
                    price=close,
                    strategy=self.name
                ))
            
            # Price at upper band - sell signal
            elif close >= data[upper].iloc[i]:
                signals.append(TradeSignal(
                    timestamp=data.index[i],
                    symbol=self.params.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType.SELL,
                    price=close,
                    strategy=self.name
                ))
        
        self._signals = signals
        return signals


class StrategyManager:
    """Manages multiple trading strategies."""
    
    # Registry of available strategies
    _STRATEGIES: Dict[str, type] = {
        'sma_crossover': SMACrossoverStrategy,
        'rsi': RSIStrategy,
        'macd': MACDStrategy,
        'bollinger_bounce': BollingerBounceStrategy,
    }
    
    def __init__(self):
        self._active_strategies: Dict[str, BaseStrategy] = {}
        self._results: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type) -> None:
        """Register a custom strategy class."""
        cls._STRATEGIES[name.lower()] = strategy_class
    
    def add_strategy(
        self, 
        name: str, 
        strategy_type: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> 'StrategyManager':
        """Add a strategy to the manager."""
        strategy_type = strategy_type.lower()
        
        if strategy_type not in self._STRATEGIES:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        self._active_strategies[name] = self._STRATEGIES[strategy_type](name, params)
        
        return self
    
    def remove_strategy(self, name: str) -> 'StrategyManager':
        """Remove a strategy from the manager."""
        if name in self._active_strategies:
            del self._active_strategies[name]
        
        return self
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name."""
        return self._active_strategies.get(name)
    
    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names."""
        return list(self._active_strategies.keys())
    
    def run_all(
        self, 
        data: pd.DataFrame, 
        symbol: str = "UNKNOWN"
    ) -> Dict[str, List[TradeSignal]]:
        """Run all active strategies on data."""
        results = {}
        
        for name, strategy in self._active_strategies.items():
            strategy.params['symbol'] = symbol
            signals = strategy.generate_signals(data)
            results[name] = signals
        
        return results
    
    def clear(self) -> 'StrategyManager':
        """Clear all strategies."""
        self._active_strategies.clear()
        self._results.clear()
        
        return self
    
    def get_available_strategies(self) -> Dict[str, str]:
        """Get list of available strategy types."""
        return {
            name: strat.__name__ 
            for name, strat in self._STRATEGIES.items()
        }


# Factory function
def create_strategy(
    strategy_type: str,
    name: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> BaseStrategy:
    """Factory function to create strategy instances."""
    strategy_type = strategy_type.lower()
    
    if strategy_type not in StrategyManager._STRATEGIES:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    name = name or strategy_type
    return StrategyManager._STRATEGIES[strategy_type](name, params)