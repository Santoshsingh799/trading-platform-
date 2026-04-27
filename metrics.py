"""
Performance Metrics Module
Calculates trading performance metrics including Sharpe ratio and max drawdown.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_holding_period: float
    volatility: float
    calmar_ratio: float


class PerformanceCalculator:
    """Calculate various performance metrics for trading strategies."""
    
    def __init__(self, risk_free_rate: float = 0.02, trading_days: int = 252):
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def calculate_returns(
        self, 
        equity_curve: pd.Series
    ) -> pd.Series:
        """Calculate returns from equity curve."""
        returns = equity_curve.pct_change().dropna()
        return returns
    
    def calculate_sharpe_ratio(
        self, 
        returns: pd.Series, 
        period: int = 252
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Formula: (Annualized Return - Risk Free Rate) / Annualized Volatility
        """
        if len(returns) == 0:
            return 0.0
        
        # Annualize the returns
        mean_return = returns.mean() * self.trading_days
        std_return = returns.std() * np.sqrt(self.trading_days)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return - self.risk_free_rate) / std_return
        
        return round(sharpe, 2)
    
    def calculate_sortino_ratio(
        self, 
        returns: pd.Series,
        target_return: float = 0.0
    ) -> float:
        """
        Calculate Sortino ratio (downside deviation).
        
        Formula: (Annualized Return - Target Return) / Downside Deviation
        """
        if len(returns) == 0:
            return 0.0
        
        # Calculate downside returns
        downside_returns = returns[returns < target_return]
        
        if len(downside_returns) == 0:
            return 0.0
        
        downside_std = downside_returns.std() * np.sqrt(self.trading_days)
        
        if downside_std == 0:
            return 0.0
        
        mean_return = returns.mean() * self.trading_days
        sortino = (mean_return - target_return) / downside_std
        
        return round(sortino, 2)
    
    def calculate_max_drawdown(
        self, 
        equity_curve: pd.Series
    ) -> Tuple[float, float]:
        """
        Calculate maximum drawdown and maximum drawdown percentage.
        
        Returns:
            Tuple of (max_drawdown, max_drawdown_pct)
        """
        if len(equity_curve) == 0:
            return 0.0, 0.0
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = equity_curve - running_max
        
        # Maximum drawdown (absolute)
        max_dd = drawdown.min()
        
        # Maximum drawdown percentage
        drawdown_pct = (drawdown / running_max) * 100
        max_dd_pct = drawdown_pct.min()
        
        return round(max_dd, 2), round(max_dd_pct, 2)
    
    def calculate_calmar_ratio(
        self, 
        returns: pd.Series,
        max_drawdown_pct: float
    ) -> float:
        """
        Calculate Calmar ratio.
        
        Formula: Annualized Return / |Max Drawdown %|
        """
        if max_drawdown_pct == 0:
            return 0.0
        
        annualized_return = returns.mean() * self.trading_days
        calmar = annualized_return / abs(max_drawdown_pct)
        
        return round(calmar, 2)
    
    def calculate_win_rate(
        self, 
        trades: List[Dict[str, Any]]
    ) -> float:
        """Calculate win rate from trades."""
        if not trades:
            return 0.0
        
        winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return round(winning / len(trades) * 100, 2)
    
    def calculate_profit_factor(
        self, 
        trades: List[Dict[str, Any]]
    ) -> float:
        """Calculate profit factor."""
        if not trades:
            return 0.0
        
        gross_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        gross_loss = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        
        if gross_loss == 0:
            return 0.0
        
        return round(gross_profit / gross_loss, 2)
    
    def calculate_all_metrics(
        self, 
        equity_curve: pd.Series,
        trades: List[Dict[str, Any]],
        entry_dates: Optional[List[datetime]] = None,
        exit_dates: Optional[List[datetime]] = None
    ) -> PerformanceMetrics:
        """Calculate all performance metrics."""
        
        # Calculate returns
        returns = self.calculate_returns(equity_curve)
        
        # Basic metrics
        total_return = ((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1) * 100 if len(equity_curve) > 1 else 0
        annualized_return = returns.mean() * self.trading_days * 100
        
        # Sharpe ratio
        sharpe = self.calculate_sharpe_ratio(returns)
        
        # Sortino ratio
        sortino = self.calculate_sortino_ratio(returns)
        
        # Max drawdown
        max_dd, max_dd_pct = self.calculate_max_drawdown(equity_curve)
        
        # Calmar ratio
        calmar = self.calculate_calmar_ratio(returns, max_dd_pct)
        
        # Trade metrics
        win_rate = self.calculate_win_rate(trades)
        profit_factor = self.calculate_profit_factor(trades)
        
        # Count trades
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
        
        # Average win/loss
        wins = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
        losses = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Average holding period
        avg_holding = 0
        if entry_dates and exit_dates:
            holding_periods = [
                (exit - entry).days 
                for entry, exit in zip(entry_dates, exit_dates)
                if exit and entry
            ]
            avg_holding = np.mean(holding_periods) if holding_periods else 0
        
        # Volatility
        volatility = returns.std() * np.sqrt(self.trading_days) * 100
        
        return PerformanceMetrics(
            total_return=round(total_return, 2),
            annualized_return=round(annualized_return, 2),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_pct=round(max_dd_pct, 2),
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            avg_holding_period=round(avg_holding, 2),
            volatility=round(volatility, 2),
            calmar_ratio=calmar
        )
    
    def generate_metrics_dataframe(
        self, 
        metrics_list: List[PerformanceMetrics],
        strategy_names: List[str]
    ) -> pd.DataFrame:
        """Generate a comparison DataFrame from multiple strategy metrics."""
        data = []
        
        for metrics, name in zip(metrics_list, strategy_names):
            data.append({
                'Strategy': name,
                'Total Return (%)': metrics.total_return,
                'Annualized Return (%)': metrics.annualized_return,
                'Sharpe Ratio': metrics.sharpe_ratio,
                'Sortino Ratio': metrics.sortino_ratio,
                'Max Drawdown (%)': metrics.max_drawdown_pct,
                'Win Rate (%)': metrics.win_rate,
                'Profit Factor': metrics.profit_factor,
                'Calmar Ratio': metrics.calmar_ratio,
                'Total Trades': metrics.total_trades,
                'Volatility (%)': metrics.volatility
            })
        
        return pd.DataFrame(data)


# Utility functions
def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Quick Sharpe ratio calculation."""
    calc = PerformanceCalculator(risk_free_rate=risk_free_rate)
    return calc.calculate_sharpe_ratio(returns)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Quick max drawdown percentage calculation."""
    calc = PerformanceCalculator()
    _, max_dd_pct = calc.calculate_max_drawdown(equity_curve)
    return max_dd_pct


def calculate_sortino(returns: pd.Series) -> float:
    """Quick Sortino ratio calculation."""
    calc = PerformanceCalculator()
    return calc.calculate_sortino_ratio(returns)