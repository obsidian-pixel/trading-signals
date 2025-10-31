"""
Technical indicators module using TA-Lib.
Provides functions for calculating various technical analysis indicators.
"""

import numpy as np
import pandas as pd
import talib
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Technical indicator calculator using TA-Lib."""
    
    @staticmethod
    def calculate_rsi(
        close: np.ndarray,
        timeperiod: int = 14
    ) -> np.ndarray:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            close: Close prices
            timeperiod: RSI period
        
        Returns:
            RSI values (0-100)
        """
        return talib.RSI(close, timeperiod=timeperiod)
    
    @staticmethod
    def calculate_macd(
        close: np.ndarray,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            close: Close prices
            fastperiod: Fast EMA period
            slowperiod: Slow EMA period
            signalperiod: Signal line period
        
        Returns:
            Tuple of (macd, signal, histogram)
        """
        macd, signal, hist = talib.MACD(
            close,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )
        return macd, signal, hist
    
    @staticmethod
    def calculate_bollinger_bands(
        close: np.ndarray,
        timeperiod: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate Bollinger Bands.
        
        Args:
            close: Close prices
            timeperiod: Moving average period
            nbdevup: Upper band standard deviations
            nbdevdn: Lower band standard deviations
        
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=timeperiod,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0  # Simple Moving Average
        )
        return upper, middle, lower
    
    @staticmethod
    def calculate_atr(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        timeperiod: int = 14
    ) -> np.ndarray:
        """
        Calculate Average True Range (ATR) - volatility indicator.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            timeperiod: ATR period
        
        Returns:
            ATR values
        """
        return talib.ATR(high, low, close, timeperiod=timeperiod)
    
    @staticmethod
    def calculate_ema(
        close: np.ndarray,
        timeperiod: int = 20
    ) -> np.ndarray:
        """
        Calculate Exponential Moving Average (EMA).
        
        Args:
            close: Close prices
            timeperiod: EMA period
        
        Returns:
            EMA values
        """
        return talib.EMA(close, timeperiod=timeperiod)
    
    @staticmethod
    def calculate_sma(
        close: np.ndarray,
        timeperiod: int = 20
    ) -> np.ndarray:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            close: Close prices
            timeperiod: SMA period
        
        Returns:
            SMA values
        """
        return talib.SMA(close, timeperiod=timeperiod)
    
    @staticmethod
    def calculate_stochastic(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        fastk_period: int = 5,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            fastk_period: Fast %K period
            slowk_period: Slow %K period
            slowd_period: Slow %D period
        
        Returns:
            Tuple of (slowk, slowd)
        """
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=0,
            slowd_period=slowd_period,
            slowd_matype=0
        )
        return slowk, slowd
    
    @staticmethod
    def calculate_adx(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        timeperiod: int = 14
    ) -> np.ndarray:
        """
        Calculate Average Directional Index (ADX) - trend strength.
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            timeperiod: ADX period
        
        Returns:
            ADX values
        """
        return talib.ADX(high, low, close, timeperiod=timeperiod)
    
    @staticmethod
    def calculate_obv(
        close: np.ndarray,
        volume: np.ndarray
    ) -> np.ndarray:
        """
        Calculate On-Balance Volume (OBV).
        
        Args:
            close: Close prices
            volume: Volume data
        
        Returns:
            OBV values
        """
        return talib.OBV(close, volume)
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators for a DataFrame.
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
        Returns:
            DataFrame with additional indicator columns
        """
        df = df.copy()
        
        # Extract price arrays
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        open_price = df['open'].values
        volume = df['volume'].values
        
        try:
            # RSI
            df['rsi'] = TechnicalIndicators.calculate_rsi(close)
            
            # MACD
            macd, signal, hist = TechnicalIndicators.calculate_macd(close)
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_hist'] = hist
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(close)
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # ATR (Volatility)
            df['atr'] = TechnicalIndicators.calculate_atr(high, low, close)
            
            # Moving Averages
            df['ema_9'] = TechnicalIndicators.calculate_ema(close, timeperiod=9)
            df['ema_21'] = TechnicalIndicators.calculate_ema(close, timeperiod=21)
            df['ema_50'] = TechnicalIndicators.calculate_ema(close, timeperiod=50)
            df['sma_20'] = TechnicalIndicators.calculate_sma(close, timeperiod=20)
            
            # Stochastic
            slowk, slowd = TechnicalIndicators.calculate_stochastic(high, low, close)
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            
            # ADX (Trend Strength)
            df['adx'] = TechnicalIndicators.calculate_adx(high, low, close)
            
            # OBV (Volume)
            df['obv'] = TechnicalIndicators.calculate_obv(close, volume)
            
            # Price-based features
            df['price_change'] = df['close'].pct_change()
            df['price_range'] = (df['high'] - df['low']) / df['close']
            df['body_size'] = abs(df['close'] - df['open']) / df['close']
            
            # Volume-based features
            df['volume_change'] = df['volume'].pct_change()
            df['volume_sma'] = TechnicalIndicators.calculate_sma(volume, timeperiod=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            logger.debug("Calculated all technical indicators")
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise
        
        return df
    
    @staticmethod
    def get_latest_indicators(df: pd.DataFrame) -> Dict[str, float]:
        """
        Get latest indicator values as a dictionary.
        
        Args:
            df: DataFrame with calculated indicators
        
        Returns:
            Dictionary of latest indicator values
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        return {
            'rsi': latest.get('rsi', np.nan),
            'macd': latest.get('macd', np.nan),
            'macd_signal': latest.get('macd_signal', np.nan),
            'macd_hist': latest.get('macd_hist', np.nan),
            'bb_upper': latest.get('bb_upper', np.nan),
            'bb_middle': latest.get('bb_middle', np.nan),
            'bb_lower': latest.get('bb_lower', np.nan),
            'bb_width': latest.get('bb_width', np.nan),
            'atr': latest.get('atr', np.nan),
            'ema_9': latest.get('ema_9', np.nan),
            'ema_21': latest.get('ema_21', np.nan),
            'ema_50': latest.get('ema_50', np.nan),
            'stoch_k': latest.get('stoch_k', np.nan),
            'stoch_d': latest.get('stoch_d', np.nan),
            'adx': latest.get('adx', np.nan),
            'obv': latest.get('obv', np.nan),
            'price_change': latest.get('price_change', np.nan),
            'volume_ratio': latest.get('volume_ratio', np.nan)
        }
    
    @staticmethod
    def validate_signal_conditions(indicators: Dict[str, float]) -> Dict[str, bool]:
        """
        Validate various trading signal conditions.
        
        Args:
            indicators: Dictionary of indicator values
        
        Returns:
            Dictionary of condition checks
        """
        rsi = indicators.get('rsi', 50)
        macd_hist = indicators.get('macd_hist', 0)
        stoch_k = indicators.get('stoch_k', 50)
        adx = indicators.get('adx', 0)
        
        return {
            'rsi_oversold': rsi < 30,
            'rsi_overbought': rsi > 70,
            'rsi_neutral': 40 <= rsi <= 60,
            'macd_bullish': macd_hist > 0,
            'macd_bearish': macd_hist < 0,
            'stoch_oversold': stoch_k < 20,
            'stoch_overbought': stoch_k > 80,
            'strong_trend': adx > 25,
            'weak_trend': adx < 20
        }


def demo_indicators():
    """Demo function to show indicator calculations."""
    # Create sample data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    np.random.seed(42)
    
    # Generate synthetic price data
    close_prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices + np.random.randn(100) * 50,
        'high': close_prices + abs(np.random.randn(100) * 100),
        'low': close_prices - abs(np.random.randn(100) * 100),
        'close': close_prices,
        'volume': abs(np.random.randn(100) * 1000)
    })
    
    print("=" * 60)
    print("TECHNICAL INDICATORS DEMO")
    print("=" * 60)
    
    # Calculate indicators
    df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)
    
    # Show latest values
    print("\n📊 Latest Indicator Values:")
    latest = TechnicalIndicators.get_latest_indicators(df_with_indicators)
    
    for key, value in latest.items():
        if not np.isnan(value):
            print(f"   {key:15s}: {value:10.2f}")
    
    # Validate signal conditions
    print("\n🚦 Signal Conditions:")
    conditions = TechnicalIndicators.validate_signal_conditions(latest)
    
    for key, value in conditions.items():
        status = "✓" if value else " "
        print(f"   [{status}] {key}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    demo_indicators()
