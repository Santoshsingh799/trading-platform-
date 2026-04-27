"""
Trade Log Export Module
Handles exporting trade logs to CSV format.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


@dataclass
class TradeLogEntry:
    """Represents a single trade log entry."""
    timestamp: datetime
    symbol: str
    action: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    commission: float = 0
    strategy: str = ""
    notes: str = ""
    order_id: str = ""
    pnl: float = 0
    pnl_pct: float = 0


class TradeLogExporter:
    """Export trade logs to various formats."""
    
    DEFAULT_COLUMNS = [
        'timestamp',
        'order_id',
        'symbol',
        'action',
        'quantity',
        'price',
        'commission',
        'strategy',
        'pnl',
        'pnl_pct',
        'notes'
    ]
    
    def __init__(self):
        self._entries: List[TradeLogEntry] = []
    
    def add_entry(
        self,
        timestamp: datetime,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        commission: float = 0,
        strategy: str = "",
        notes: str = "",
        order_id: str = "",
        pnl: float = 0,
        pnl_pct: float = 0
    ) -> 'TradeLogExporter':
        """Add a trade log entry."""
        entry = TradeLogEntry(
            timestamp=timestamp,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            commission=commission,
            strategy=strategy,
            notes=notes,
            order_id=order_id,
            pnl=pnl,
            pnl_pct=pnl_pct
        )
        self._entries.append(entry)
        
        return self
    
    def add_entries_from_list(
        self, 
        entries: List[Dict[str, Any]]
    ) -> 'TradeLogExporter':
        """Add multiple entries from a list of dictionaries."""
        for entry in entries:
            self.add_entry(
                timestamp=entry.get('timestamp', datetime.now()),
                symbol=entry.get('symbol', ''),
                action=entry.get('action', ''),
                quantity=entry.get('quantity', 0),
                price=entry.get('price', 0),
                commission=entry.get('commission', 0),
                strategy=entry.get('strategy', ''),
                notes=entry.get('notes', ''),
                order_id=entry.get('order_id', ''),
                pnl=entry.get('pnl', 0),
                pnl_pct=entry.get('pnl_pct', 0)
            )
        
        return self
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert entries to pandas DataFrame."""
        if not self._entries:
            return pd.DataFrame(columns=self.DEFAULT_COLUMNS)
        
        data = []
        for entry in self._entries:
            data.append({
                'timestamp': entry.timestamp,
                'order_id': entry.order_id,
                'symbol': entry.symbol,
                'action': entry.action,
                'quantity': entry.quantity,
                'price': entry.price,
                'commission': entry.commission,
                'strategy': entry.strategy,
                'pnl': entry.pnl,
                'pnl_pct': entry.pnl_pct,
                'notes': entry.notes
            })
        
        return pd.DataFrame(data)
    
    def to_csv(
        self, 
        filepath: Union[str, Path],
        include_headers: bool = True,
        date_format: str = "%Y-%m-%d %H:%M:%S"
    ) -> bool:
        """Export trade log to CSV file."""
        if not self._entries:
            return False
        
        df = self.to_dataframe()
        
        # Format timestamp
        df['timestamp'] = df['timestamp'].dt.strftime(date_format)
        
        # Save to CSV
        df.to_csv(filepath, index=False, header=include_headers)
        
        return True
    
    def to_excel(
        self, 
        filepath: Union[str, Path],
        sheet_name: str = "Trade Log"
    ) -> bool:
        """Export trade log to Excel file."""
        if not self._entries:
            return False
        
        df = self.to_dataframe()
        df.to_excel(filepath, sheet_name=sheet_name, index=False)
        
        return True
    
    def filter_by_symbol(self, symbol: str) -> 'TradeLogExporter':
        """Filter entries by symbol."""
        filtered = TradeLogExporter()
        filtered._entries = [
            e for e in self._entries 
            if e.symbol.upper() == symbol.upper()
        ]
        return filtered
    
    def filter_by_strategy(self, strategy: str) -> 'TradeLogExporter':
        """Filter entries by strategy."""
        filtered = TradeLogExporter()
        filtered._entries = [
            e for e in self._entries 
            if e.strategy.upper() == strategy.upper()
        ]
        return filtered
    
    def filter_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> 'TradeLogExporter':
        """Filter entries by date range."""
        filtered = TradeLogExporter()
        filtered._entries = [
            e for e in self._entries 
            if start_date <= e.timestamp <= end_date
        ]
        return filtered
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the trade log."""
        if not self._entries:
            return {
                'total_trades': 0,
                'total_volume': 0,
                'total_commission': 0,
                'total_pnl': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }
        
        total_trades = len(self._entries)
        buys = sum(1 for e in self._entries if e.action.upper() == 'BUY')
        sells = sum(1 for e in self._entries if e.action.upper() == 'SELL')
        total_volume = sum(e.quantity * e.price for e in self._entries)
        total_commission = sum(e.commission for e in self._entries)
        total_pnl = sum(e.pnl for e in self._entries)
        winning_trades = sum(1 for e in self._entries if e.pnl > 0)
        losing_trades = sum(1 for e in self._entries if e.pnl < 0)
        
        return {
            'total_trades': total_trades,
            'buy_trades': buys,
            'sell_trades': sells,
            'total_volume': round(total_volume, 2),
            'total_commission': round(total_commission, 2),
            'total_pnl': round(total_pnl, 2),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(winning_trades / total_trades * 100, 2) if total_trades > 0 else 0
        }
    
    def clear(self) -> 'TradeLogExporter':
        """Clear all entries."""
        self._entries.clear()
        return self
    
    @property
    def entries(self) -> List[TradeLogEntry]:
        """Get all entries."""
        return self._entries.copy()
    
    @property
    def count(self) -> int:
        """Get number of entries."""
        return len(self._entries)


# Utility functions
def export_trades_to_csv(
    trades: List[Dict[str, Any]],
    filepath: Union[str, Path],
    date_format: str = "%Y-%m-%d %H:%M:%S"
) -> bool:
    """Quick export function for list of trade dictionaries."""
    exporter = TradeLogExporter()
    exporter.add_entries_from_list(trades)
    return exporter.to_csv(filepath, date_format=date_format)


def load_trades_from_csv(filepath: Union[str, Path]) -> pd.DataFrame:
    """Load trade log from CSV file."""
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df