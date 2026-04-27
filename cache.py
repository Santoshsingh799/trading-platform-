"""
Multi-Timeframe Caching System
Provides efficient data caching across different timeframes with LRU eviction.
"""

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""
    data: pd.DataFrame
    timestamp: datetime
    timeframe: str
    symbol: str
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    
    def is_expired(self, ttl_seconds: int) -> bool:
        return (datetime.now() - self.timestamp).total_seconds() > ttl_seconds


class MultiTimeframeCache:
    """
    Thread-safe LRU cache for multi-timeframe trading data.
    Supports automatic expiration and memory management.
    """
    
    TIMEFRAME_MINUTES = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440, '1w': 10080
    }
    
    def __init__(self, max_size_mb: float = 500, default_ttl: int = 300):
        self._cache: OrderedDict[Tuple[str, str], CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size_mb = max_size_mb
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._stats_lock = threading.Lock()
    
    def _estimate_size(self, df: pd.DataFrame) -> float:
        """Estimate memory size of DataFrame in MB."""
        return df.memory_usage(deep=True).sum() / (1024 * 1024)
    
    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds size limit."""
        current_size = sum(
            self._estimate_size(e.data) for e in self._cache.values()
        )
        
        while current_size > self._max_size_mb and self._cache:
            _, entry = self._cache.popitem(last=False)
            current_size -= self._estimate_size(entry.data)
    
    def _make_key(self, symbol: str, timeframe: str) -> Tuple[str, str]:
        return (symbol.upper(), timeframe.lower())
    
    def get(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Retrieve data from cache if not expired."""
        key = self._make_key(symbol, timeframe)
        
        with self._lock:
            if key not in self._cache:
                with self._stats_lock:
                    self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired(self._default_ttl):
                del self._cache[key]
                with self._stats_lock:
                    self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_access = datetime.now()
            
            with self._stats_lock:
                self._hits += 1
            
            return entry.data.copy()
    
    def set(self, symbol: str, timeframe: str, data: pd.DataFrame) -> None:
        """Store data in cache with automatic eviction."""
        key = self._make_key(symbol, timeframe)
        
        with self._lock:
            entry = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                timeframe=timeframe,
                symbol=symbol.upper()
            )
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._evict_if_needed()
    
    def invalidate(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """Invalidate cache entries matching criteria."""
        count = 0
        
        with self._lock:
            if symbol is None and timeframe is None:
                count = len(self._cache)
                self._cache.clear()
            else:
                keys_to_remove = [
                    k for k in self._cache.keys()
                    if (symbol is None or k[0] == symbol.upper()) and
                       (timeframe is None or k[1] == timeframe.lower())
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                    count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._stats_lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'entries': len(self._cache),
                'size_mb': sum(
                    self._estimate_size(e.data) 
                    for e in self._cache.values()
                )
            }
    
    def preload_timeframes(self, symbol: str, timeframes: list, data_loader) -> Dict[str, pd.DataFrame]:
        """Preload multiple timeframes for a symbol."""
        results = {}
        
        for tf in timeframes:
            data = self.get(symbol, tf)
            if data is None:
                data = data_loader(symbol, tf)
                if data is not None:
                    self.set(symbol, tf, data)
            results[tf] = data
        
        return {k: v for k, v in results.items() if v is not None}


# Global cache instance
_global_cache: Optional[MultiTimeframeCache] = None


def get_cache() -> MultiTimeframeCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiTimeframeCache()
    return _global_cache