"""
Data fetcher module that combines Binance API client with database storage.
Handles both historical data downloads and real-time streaming.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from .binance_client import BinanceDataClient, klines_to_dict
from .database import TradingDatabase, get_database

logger = logging.getLogger(__name__)


class DataFetcher:
    """Orchestrates data fetching and storage."""
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        db_path: str = "data/bitcoin.db"
    ):
        """
        Initialize data fetcher.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            api_key: Binance API key (optional)
            api_secret: Binance API secret (optional)
            db_path: Database file path
        """
        self.symbol = symbol
        self.interval = interval
        
        self.client = BinanceDataClient(api_key=api_key, api_secret=api_secret)
        self.db = get_database(db_path)
        
        logger.info(f"DataFetcher initialized for {symbol} ({interval})")
    
    def fetch_and_store_historical(self, days: int = 7) -> int:
        """
        Fetch historical data and store in database.
        
        Args:
            days: Number of days to fetch
        
        Returns:
            Number of records stored
        """
        logger.info(f"Fetching {days} days of historical data...")
        
        # Get klines from Binance
        klines = self.client.get_klines_batch(
            symbol=self.symbol,
            interval=self.interval,
            days=days
        )
        
        if not klines:
            logger.warning("No klines retrieved")
            return 0
        
        # Convert to structured format
        klines_dict = klines_to_dict(klines)
        
        # Prepare data for database insertion
        data_tuples = [
            (
                k['timestamp'],
                k['open'],
                k['high'],
                k['low'],
                k['close'],
                k['volume'],
                k.get('quote_volume'),
                k.get('trades_count')
            )
            for k in klines_dict
        ]
        
        # Insert into database
        inserted = self.db.insert_ohlcv(data_tuples)
        
        logger.info(f"Stored {inserted} records in database")
        return inserted
    
    def update_recent_data(self, limit: int = 100) -> int:
        """
        Update with most recent klines.
        
        Args:
            limit: Number of recent klines to fetch
        
        Returns:
            Number of records stored
        """
        # Get latest timestamp from database
        latest_ts = self.db.get_latest_timestamp()
        
        if latest_ts:
            start_time = datetime.fromtimestamp(latest_ts / 1000)
            logger.info(f"Updating data from {start_time}")
        else:
            # No data in DB, fetch last N klines
            start_time = datetime.utcnow() - timedelta(minutes=limit)
            logger.info("No existing data, fetching recent klines")
        
        klines = self.client.get_historical_klines(
            symbol=self.symbol,
            interval=self.interval,
            start_time=start_time,
            limit=limit
        )
        
        if not klines:
            logger.debug("No new klines to update")
            return 0
        
        klines_dict = klines_to_dict(klines)
        
        data_tuples = [
            (
                k['timestamp'],
                k['open'],
                k['high'],
                k['low'],
                k['close'],
                k['volume'],
                k.get('quote_volume'),
                k.get('trades_count')
            )
            for k in klines_dict
        ]
        
        inserted = self.db.insert_ohlcv(data_tuples)
        logger.debug(f"Updated {inserted} new records")
        
        return inserted
    
    async def stream_live_data(self, callback: Optional[callable] = None):
        """
        Stream live kline data and store in database.
        
        Args:
            callback: Optional async callback function for each kline
        """
        logger.info("Starting live data stream...")
        
        async def handle_kline(kline_data: dict):
            """Handle incoming kline data."""
            # Store in database
            data_tuple = (
                kline_data['timestamp'],
                kline_data['open'],
                kline_data['high'],
                kline_data['low'],
                kline_data['close'],
                kline_data['volume'],
                kline_data.get('quote_volume'),
                kline_data.get('trades_count')
            )
            
            self.db.insert_ohlcv([data_tuple])
            
            logger.debug(
                f"Stored kline: {datetime.fromtimestamp(kline_data['timestamp']/1000)} "
                f"| Close: ${kline_data['close']:,.2f}"
            )
            
            # Call user callback if provided
            if callback:
                await callback(kline_data)
        
        # Start streaming
        await self.client.stream_klines(
            symbol=self.symbol,
            interval=self.interval,
            callback=handle_kline
        )
    
    def get_latest_data(self, limit: int = 100) -> pd.DataFrame:
        """
        Get latest data from database.
        
        Args:
            limit: Number of records to retrieve
        
        Returns:
            DataFrame with OHLCV data
        """
        return self.db.get_ohlcv(limit=limit)
    
    def get_data_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Get data for a specific time range.
        
        Args:
            start_time: Start datetime
            end_time: End datetime
        
        Returns:
            DataFrame with OHLCV data
        """
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        return self.db.get_ohlcv(
            start_time=start_ms,
            end_time=end_ms,
            limit=100000  # Large limit for range queries
        )
    
    def ensure_data_availability(self, min_records: int = 1000) -> bool:
        """
        Ensure minimum amount of data is available in database.
        
        Args:
            min_records: Minimum number of records required
        
        Returns:
            True if sufficient data available
        """
        stats = self.db.get_data_stats()
        current_records = stats['ohlcv_count']
        
        logger.info(f"Database contains {current_records} records")
        
        if current_records >= min_records:
            logger.info(f"✓ Sufficient data available ({current_records} >= {min_records})")
            return True
        
        # Need to fetch more data
        records_needed = min_records - current_records
        
        # Assuming 1-minute intervals, calculate days needed
        # 1440 minutes per day
        minutes_per_day = 1440
        days_needed = max(1, (records_needed // minutes_per_day) + 1)
        
        logger.info(f"Fetching ~{days_needed} days to reach {min_records} records...")
        self.fetch_and_store_historical(days=days_needed)
        
        # Verify
        stats = self.db.get_data_stats()
        final_records = stats['ohlcv_count']
        
        success = final_records >= min_records
        logger.info(f"Data preparation {'successful' if success else 'failed'}: {final_records} records")
        
        return success
    
    def close(self):
        """Close connections."""
        self.db.close()
        logger.info("DataFetcher closed")


async def demo_live_stream():
    """Demo function for live data streaming."""
    fetcher = DataFetcher(symbol="BTCUSDT", interval="1m")
    
    async def on_kline(kline):
        print(f"\n📊 New Kline:")
        print(f"   Time: {datetime.fromtimestamp(kline['timestamp']/1000)}")
        print(f"   Open: ${kline['open']:,.2f}")
        print(f"   High: ${kline['high']:,.2f}")
        print(f"   Low: ${kline['low']:,.2f}")
        print(f"   Close: ${kline['close']:,.2f}")
        print(f"   Volume: {kline['volume']:.2f} BTC")
    
    try:
        await fetcher.stream_live_data(callback=on_kline)
    except KeyboardInterrupt:
        print("\n\nStream stopped by user")
    finally:
        fetcher.close()


def demo_historical_fetch():
    """Demo function for historical data fetching."""
    fetcher = DataFetcher(symbol="BTCUSDT", interval="1m")
    
    print("=" * 60)
    print("HISTORICAL DATA FETCH DEMO")
    print("=" * 60)
    
    # Fetch 1 day of data
    print("\n📥 Fetching 1 day of historical data...")
    records = fetcher.fetch_and_store_historical(days=1)
    print(f"✓ Stored {records} records")
    
    # Get latest data
    print("\n📊 Latest 10 records:")
    df = fetcher.get_latest_data(limit=10)
    print(df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_string())
    
    # Database stats
    print("\n📈 Database Statistics:")
    stats = fetcher.db.get_data_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    fetcher.close()
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "live":
        # Run live stream demo
        asyncio.run(demo_live_stream())
    else:
        # Run historical fetch demo
        demo_historical_fetch()
