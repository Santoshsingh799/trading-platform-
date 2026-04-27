import pandas as pd
import numpy as np

class PerformanceMetrics:
    @staticmethod
    def calculate(trades, initial_balance):
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "average_rr": 0.0
            }

        closed_trades = [t for t in trades if t['status'] == 'CLOSED']
        total_trades = len(closed_trades)
        if total_trades == 0:
            return {"total_trades": 0, "win_rate": 0.0, "total_profit": 0.0, "max_drawdown": 0.0, "average_rr": 0.0}

        winning_trades = sum(1 for t in closed_trades if t['pnl'] > 0)
        win_rate = (winning_trades / total_trades) * 100
        total_profit = sum(t['pnl'] for t in closed_trades)
        
        # Calculate Equity Curve & Max Drawdown
        equity = initial_balance
        peak = equity
        max_dd = 0
        for t in closed_trades:
            equity += t['pnl']
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
                
        # Average RR
        rrs = [t.get('rr_ratio', 0) for t in closed_trades if t.get('rr_ratio', 0) > 0]
        avg_rr = np.mean(rrs) if rrs else 0.0

        return {"total_trades": total_trades, "win_rate": win_rate, "total_profit": total_profit, "max_drawdown": max_dd, "average_rr": avg_rr}