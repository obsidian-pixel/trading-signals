"""
Binance API client for fetching real-time and historical Bitcoin data.
Supports both REST API and WebSocket streaming with error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import time

from binance.client import Client
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException, BinanceRequestException

logger = logging.getLogger(__name__)


class BinanceDataClient:
    """
    Binance API client for cryptocurrency data.
    Supports both synchronous and asynchronous operations.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False
    ):
        """
        Initialize Binance client.
        
        Args:
            api_key: Binance API key (optional for public data)
            api_secret: Binance API secret (optional for public data)
            testnet: Use testnet endpoints
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Initialize synchronous client
        self.client = Client(api_key, api_secret, testnet=testnet)
        
        # Async client (initialized when needed)
        self.async_client: Optional[AsyncClient] = None
        self.socket_manager: Optional[BinanceSocketManager] = None
        
        logger.info(f"Binance client initialized (testnet={testnet})")
    
    async def _init_async_client(self):
        """Initialize async client if not already done."""
        if self.async_client is None:
            self.async_client = await AsyncClient.create(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            self.socket_manager = BinanceSocketManager(self.async_client)
            logger.info("Async client initialized")
    
    def get_current_price(self, symbol: str = "BTCUSDT") -> float:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair symbol (default: BTCUSDT)
        
        Returns:
            Current price as float
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.debug(f"{symbol} current price: ${price:,.2f}")
            return price
        
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Error fetching current price: {e}")
            raise
    
    def get_historical_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[List]:
        """
        Get historical kline/candlestick data.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, etc.)
            start_time: Start time for historical data
            end_time: End time for historical data
            limit: Number of klines to retrieve (max 1000 per request)
        
        Returns:
            List of kline data [timestamp, open, high, low, close, volume, ...]
        """
        try:
            # Convert datetime to milliseconds
            start_str = str(int(start_time.timestamp() * 1000)) if start_time else None
            end_str = str(int(end_time.timestamp() * 1000)) if end_time else None
            
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str,
                limit=limit
            )
            
            logger.info(f"Retrieved {len(klines)} klines for {symbol} ({interval})")
            return klines
        
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Error fetching historical klines: {e}")
            raise
    
    def get_klines_batch(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        days: int = 7
    ) -> List[List]:
        """
        Get historical klines for multiple days (handles pagination).
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            days: Number of days to retrieve
        
        Returns:
            Combined list of all klines
        """
        all_klines = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"Fetching {days} days of {interval} data for {symbol}")
        
        # Binance limits to 1000 klines per request
        # For 1m interval, 1000 klines = ~16.7 hours
        max_klines_per_request = 1000
        
        current_start = start_time
        batch_count = 0
        
        while current_start < end_time:
            try:
                klines = self.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=current_start,
                    end_time=end_time,
                    limit=max_klines_per_request
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                batch_count += 1
                
                # Update start time to last kline's close time
                last_kline_time = datetime.fromtimestamp(klines[-1][0] / 1000)
                current_start = last_kline_time + timedelta(minutes=1)
                
                # Rate limiting: sleep briefly between requests
                time.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"Error in batch {batch_count}: {e}")
                break
        
        logger.info(f"Retrieved total of {len(all_klines)} klines in {batch_count} batches")
        return all_klines
    
    async def stream_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1m",
        callback: callable = None
    ):
        """
        Stream real-time kline data via WebSocket.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval
            callback: Async function to call with each kline update
        """
        await self._init_async_client()
        
        logger.info(f"Starting kline stream for {symbol} ({interval})")
        
        async with self.socket_manager.kline_socket(symbol=symbol, interval=interval) as stream:
            while True:
                try:
                    msg = await stream.recv()
                    
                    if msg:
                        kline = msg.get('k')
                        if kline and kline.get('x'):  # Kline is closed
                            data = {
                                'timestamp': kline['t'],
                                'open': float(kline['o']),
                                'high': float(kline['h']),
                                'low': float(kline['l']),
                                'close': float(kline['c']),
                                'volume': float(kline['v']),
                                'quote_volume': float(kline['q']),
                                'trades_count': kline['n']
                            }
                            
                            if callback:
                                await callback(data)
                            else:
                                logger.debug(f"Kline update: {data}")
                
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    await asyncio.sleep(5)  # Reconnect delay
    
    async def stream_ticker(
        self,
        symbol: str = "BTCUSDT",
        callback: callable = None
    ):
        """
        Stream real-time ticker data via WebSocket.
        
        Args:
            symbol: Trading pair symbol
            callback: Async function to call with each ticker update
        """
        await self._init_async_client()
        
        logger.info(f"Starting ticker stream for {symbol}")
        
        async with self.socket_manager.symbol_ticker_socket(symbol=symbol) as stream:
            while True:
                try:
                    msg = await stream.recv()
                    
                    if msg:
                        data = {
                            'symbol': msg['s'],
                            'price': float(msg['c']),
                            'volume_24h': float(msg['v']),
                            'price_change_24h': float(msg['p']),
                            'price_change_pct_24h': float(msg['P']),
                            'high_24h': float(msg['h']),
                            'low_24h': float(msg['l'])
                        }
                        
                        if callback:
                            await callback(data)
                        else:
                            logger.debug(f"Ticker update: {data}")
                
                except Exception as e:
                    logger.error(f"Ticker stream error: {e}")
                    await asyncio.sleep(5)
    
    def get_exchange_info(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Get exchange trading rules and symbol information.
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Exchange information dictionary
        """
        try:
            info = self.client.get_symbol_info(symbol=symbol)
            logger.debug(f"Exchange info for {symbol}: {info}")
            return info
        
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Error fetching exchange info: {e}")
            raise
    
    def get_server_time(self) -> int:
        """
        Get Binance server time (useful for time synchronization).
        
        Returns:
            Server timestamp in milliseconds
        """
        try:
            server_time = self.client.get_server_time()
            return server_time['serverTime']
        
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Error fetching server time: {e}")
            raise
    
    async def close(self):
        """Close async client connections."""
        if self.async_client:
            await self.async_client.close_connection()
            logger.info("Async client connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._init_async_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Utility functions

def klines_to_dict(klines: List[List]) -> List[Dict]:
    """
    Convert raw kline data to structured dictionaries.
    
    Args:
        klines: Raw kline data from Binance API
    
    Returns:
        List of dictionaries with labeled kline data
    """
    return [
        {
            'timestamp': kline[0],
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5]),
            'close_time': kline[6],
            'quote_volume': float(kline[7]),
            'trades_count': kline[8],
            'taker_buy_base': float(kline[9]),
            'taker_buy_quote': float(kline[10])
        }
        for kline in klines
    ]


async def test_connection():
    """Test Binance API connection."""
    client = BinanceDataClient()
    
    try:
        # Test REST API
        price = client.get_current_price("BTCUSDT")
        print(f"✓ REST API working - Current BTC price: ${price:,.2f}")
        
        # Test server time
        server_time = client.get_server_time()
        print(f"✓ Server time: {datetime.fromtimestamp(server_time/1000)}")
        
        # Test historical data
        klines = client.get_historical_klines(
            symbol="BTCUSDT",
            interval="1m",
            limit=10
        )
        print(f"✓ Historical data: Retrieved {len(klines)} klines")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    # Run connection test
    asyncio.run(test_connection())
