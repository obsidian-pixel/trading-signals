"""
Database module for storing Bitcoin OHLCV data and trading signals.
Uses SQLite for local storage with optimized schema for time-series queries.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingDatabase:
    """SQLite database manager for trading data."""
    
    def __init__(self, db_path: str = "data/bitcoin.db"):
        """Initialize database connection and create tables."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            # Enable WAL mode for better concurrency
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # OHLCV data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL,
                trades_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp)
            )
        """)
        
        # Create index on timestamp for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlcv_timestamp 
            ON ohlcv(timestamp DESC)
        """)
        
        # Trading signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                predicted_direction TEXT,
                lstm_prediction REAL,
                cnn_prediction REAL,
                rf_prediction REAL,
                xgb_prediction REAL,
                ensemble_prediction REAL,
                rsi REAL,
                macd REAL,
                bb_upper REAL,
                bb_lower REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp 
            ON signals(timestamp DESC)
        """)
        
        # Trades table (for backtesting/paper trading)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_timestamp INTEGER NOT NULL,
                exit_timestamp INTEGER,
                entry_price REAL NOT NULL,
                exit_price REAL,
                position_size REAL NOT NULL,
                profit_loss REAL,
                profit_loss_pct REAL,
                trade_duration_seconds INTEGER,
                status TEXT DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def insert_ohlcv(self, data: List[Tuple]) -> int:
        """
        Insert OHLCV data into database.
        
        Args:
            data: List of tuples (timestamp, open, high, low, close, volume, ...)
        
        Returns:
            Number of rows inserted
        """
        cursor = self.conn.cursor()
        inserted = 0
        
        for row in data:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO ohlcv 
                    (timestamp, open, high, low, close, volume, quote_volume, trades_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, row[:8])  # Take first 8 elements
                inserted += cursor.rowcount
            except sqlite3.Error as e:
                logger.warning(f"Error inserting row: {e}")
                continue
        
        self.conn.commit()
        logger.debug(f"Inserted {inserted} OHLCV records")
        return inserted
    
    def insert_ohlcv_df(self, df: pd.DataFrame) -> int:
        """
        Insert OHLCV data from DataFrame.
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
        
        Returns:
            Number of rows inserted
        """
        df_copy = df.copy()
        
        # Ensure required columns exist
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df_copy.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Add optional columns if missing
        if 'quote_volume' not in df_copy.columns:
            df_copy['quote_volume'] = None
        if 'trades_count' not in df_copy.columns:
            df_copy['trades_count'] = None
        
        # Convert to list of tuples
        data = df_copy[required_cols + ['quote_volume', 'trades_count']].values.tolist()
        return self.insert_ohlcv(data)
    
    def get_ohlcv(
        self, 
        limit: int = 1000, 
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Retrieve OHLCV data from database.
        
        Args:
            limit: Maximum number of records to retrieve
            start_time: Start timestamp (milliseconds)
            end_time: End timestamp (milliseconds)
        
        Returns:
            DataFrame with OHLCV data
        """
        query = "SELECT * FROM ohlcv WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                # Sort by timestamp ascending for chronological order
                df = df.sort_values('timestamp').reset_index(drop=True)
                logger.debug(f"Retrieved {len(df)} OHLCV records")
            
            return df
        
        except sqlite3.Error as e:
            logger.error(f"Error retrieving OHLCV data: {e}")
            return pd.DataFrame()
    
    def get_latest_timestamp(self) -> Optional[int]:
        """Get the timestamp of the most recent OHLCV record."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM ohlcv")
        result = cursor.fetchone()
        return result[0] if result[0] else None
    
    def insert_signal(
        self,
        timestamp: int,
        signal_type: str,
        confidence: float,
        predicted_direction: str,
        model_predictions: dict,
        indicators: dict
    ) -> int:
        """
        Insert trading signal into database.
        
        Args:
            timestamp: Signal timestamp (milliseconds)
            signal_type: 'BUY', 'SELL', or 'HOLD'
            confidence: Prediction confidence (0-1)
            predicted_direction: 'UP', 'DOWN', or 'NEUTRAL'
            model_predictions: Dict with model outputs
            indicators: Dict with technical indicators
        
        Returns:
            Signal ID
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO signals (
                timestamp, signal_type, confidence, predicted_direction,
                lstm_prediction, cnn_prediction, rf_prediction, xgb_prediction, ensemble_prediction,
                rsi, macd, bb_upper, bb_lower
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            signal_type,
            confidence,
            predicted_direction,
            model_predictions.get('lstm'),
            model_predictions.get('cnn'),
            model_predictions.get('rf'),
            model_predictions.get('xgb'),
            model_predictions.get('ensemble'),
            indicators.get('rsi'),
            indicators.get('macd'),
            indicators.get('bb_upper'),
            indicators.get('bb_lower')
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_signals(self, limit: int = 100) -> pd.DataFrame:
        """Retrieve recent trading signals."""
        query = "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?"
        
        try:
            df = pd.read_sql_query(query, self.conn, params=[limit])
            if not df.empty:
                df = df.sort_values('timestamp').reset_index(drop=True)
            return df
        except sqlite3.Error as e:
            logger.error(f"Error retrieving signals: {e}")
            return pd.DataFrame()
    
    def record_trade(
        self,
        entry_timestamp: int,
        entry_price: float,
        position_size: float
    ) -> int:
        """
        Record a new trade entry.
        
        Returns:
            Trade ID
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (entry_timestamp, entry_price, position_size, status)
            VALUES (?, ?, ?, 'OPEN')
        """, (entry_timestamp, entry_price, position_size))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def close_trade(
        self,
        trade_id: int,
        exit_timestamp: int,
        exit_price: float
    ) -> None:
        """Close an open trade and calculate profit/loss."""
        cursor = self.conn.cursor()
        
        # Get entry price
        cursor.execute("SELECT entry_price, position_size FROM trades WHERE id = ?", (trade_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.warning(f"Trade ID {trade_id} not found")
            return
        
        entry_price, position_size = result
        
        # Calculate P/L
        profit_loss = (exit_price - entry_price) * position_size
        profit_loss_pct = ((exit_price - entry_price) / entry_price) * 100
        
        cursor.execute("""
            UPDATE trades SET
                exit_timestamp = ?,
                exit_price = ?,
                profit_loss = ?,
                profit_loss_pct = ?,
                status = 'CLOSED'
            WHERE id = ?
        """, (exit_timestamp, exit_price, profit_loss, profit_loss_pct, trade_id))
        
        self.conn.commit()
        logger.info(f"Trade {trade_id} closed: P/L = ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
    
    def get_trades(self, status: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
        """Retrieve trades."""
        query = "SELECT * FROM trades"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY entry_timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:
            return pd.read_sql_query(query, self.conn, params=params)
        except sqlite3.Error as e:
            logger.error(f"Error retrieving trades: {e}")
            return pd.DataFrame()
    
    def get_data_stats(self) -> dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM ohlcv")
        ohlcv_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM signals")
        signals_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trades")
        trades_count = cursor.fetchone()[0]
        
        # Get date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM ohlcv")
        min_ts, max_ts = cursor.fetchone()
        
        return {
            'ohlcv_count': ohlcv_count,
            'signals_count': signals_count,
            'trades_count': trades_count,
            'earliest_timestamp': min_ts,
            'latest_timestamp': max_ts,
            'date_range_days': (max_ts - min_ts) / (1000 * 60 * 60 * 24) if min_ts and max_ts else 0
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
_db_instance: Optional[TradingDatabase] = None


def get_database(db_path: str = "data/bitcoin.db") -> TradingDatabase:
    """Get or create database singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TradingDatabase(db_path)
    return _db_instance
