"""
Feature engineering module for preparing data for ML models.
Handles normalization, sliding windows, and feature selection.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Prepares features for machine learning models."""
    
    def __init__(self, lookback_period: int = 60):
        """
        Initialize feature engineer.
        
        Args:
            lookback_period: Number of time steps to look back
        """
        self.lookback_period = lookback_period
        self.scaler = StandardScaler()
        self.price_scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_fitted = False
        
        logger.info(f"FeatureEngineer initialized with lookback={lookback_period}")
    
    def create_sequences(
        self,
        data: np.ndarray,
        labels: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Create sliding window sequences for time-series prediction.
        
        Args:
            data: Input data array (samples, features)
            labels: Optional labels for supervised learning
        
        Returns:
            Tuple of (sequences, sequence_labels)
        """
        sequences = []
        sequence_labels = [] if labels is not None else None
        
        for i in range(len(data) - self.lookback_period):
            # Extract window
            seq = data[i:i + self.lookback_period]
            sequences.append(seq)
            
            if labels is not None:
                # Label is the next value after the window
                sequence_labels.append(labels[i + self.lookback_period])
        
        sequences = np.array(sequences)
        
        if labels is not None:
            sequence_labels = np.array(sequence_labels)
            logger.debug(f"Created {len(sequences)} sequences with labels")
            return sequences, sequence_labels
        
        logger.debug(f"Created {len(sequences)} sequences")
        return sequences, None
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Select and prepare features from DataFrame with indicators.
        
        Args:
            df: DataFrame with OHLCV and indicator columns
        
        Returns:
            DataFrame with selected features
        """
        feature_columns = [
            # Price features
            'close', 'open', 'high', 'low',
            'price_change', 'price_range', 'body_size',
            
            # Volume features
            'volume', 'volume_change', 'volume_ratio',
            
            # Indicators
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'atr', 'ema_9', 'ema_21', 'ema_50',
            'stoch_k', 'stoch_d', 'adx', 'obv'
        ]
        
        # Select available columns
        available_cols = [col for col in feature_columns if col in df.columns]
        
        if len(available_cols) == 0:
            raise ValueError("No feature columns found in DataFrame")
        
        features_df = df[available_cols].copy()
        
        # Fill NaN values (from indicator calculations)
        features_df = features_df.fillna(method='bfill').fillna(method='ffill')
        
        logger.debug(f"Prepared {len(available_cols)} feature columns")
        return features_df
    
    def fit_scalers(self, df: pd.DataFrame):
        """
        Fit scalers on training data.
        
        Args:
            df: Training DataFrame with features
        """
        features_df = self.prepare_features(df)
        
        # Fit standard scaler on all features
        self.scaler.fit(features_df.values)
        
        # Fit price scaler on close prices only
        if 'close' in features_df.columns:
            self.price_scaler.fit(features_df[['close']].values)
        
        self.is_fitted = True
        logger.info("Scalers fitted on training data")
    
    def transform_features(self, df: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """
        Transform features using fitted scalers.
        
        Args:
            df: DataFrame with features
            fit: Whether to fit scalers (for training data)
        
        Returns:
            Normalized feature array
        """
        features_df = self.prepare_features(df)
        
        if fit:
            self.fit_scalers(df)
        
        if not self.is_fitted:
            raise ValueError("Scalers not fitted. Call fit_scalers() first.")
        
        # Normalize features
        normalized = self.scaler.transform(features_df.values)
        
        logger.debug(f"Transformed features: shape {normalized.shape}")
        return normalized
    
    def create_labels(
        self,
        df: pd.DataFrame,
        prediction_horizon: int = 1,
        threshold: float = 0.0005  # 0.05% price change
    ) -> np.ndarray:
        """
        Create labels for classification (UP=1, DOWN=0, HOLD=2).
        
        Args:
            df: DataFrame with price data
            prediction_horizon: Steps ahead to predict
            threshold: Minimum price change to classify as UP/DOWN
        
        Returns:
            Array of labels
        """
        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")
        
        close_prices = df['close'].values
        labels = []
        
        for i in range(len(close_prices) - prediction_horizon):
            current_price = close_prices[i]
            future_price = close_prices[i + prediction_horizon]
            
            price_change = (future_price - current_price) / current_price
            
            if price_change > threshold:
                labels.append(1)  # UP
            elif price_change < -threshold:
                labels.append(0)  # DOWN
            else:
                labels.append(2)  # HOLD
        
        # Pad remaining with HOLD
        labels.extend([2] * prediction_horizon)
        
        return np.array(labels)
    
    def prepare_train_data(
        self,
        df: pd.DataFrame,
        prediction_horizon: int = 1,
        train_split: float = 0.8
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare complete training and validation datasets.
        
        Args:
            df: DataFrame with OHLCV and indicators
            prediction_horizon: Steps ahead to predict
            train_split: Fraction of data for training
        
        Returns:
            Tuple of (X_train, X_val, y_train, y_val)
        """
        # Transform features
        features = self.transform_features(df, fit=True)
        
        # Create labels
        labels = self.create_labels(df, prediction_horizon=prediction_horizon)
        
        # Create sequences
        X, y = self.create_sequences(features, labels)
        
        # Split into train/validation
        split_idx = int(len(X) * train_split)
        
        X_train = X[:split_idx]
        X_val = X[split_idx:]
        y_train = y[:split_idx]
        y_val = y[split_idx:]
        
        logger.info(
            f"Prepared data - Train: {X_train.shape}, Val: {X_val.shape}, "
            f"Features: {X_train.shape[2]}"
        )
        
        return X_train, X_val, y_train, y_val
    
    def prepare_inference_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare data for real-time inference.
        
        Args:
            df: DataFrame with recent OHLCV and indicators
        
        Returns:
            Sequence ready for model prediction
        """
        if not self.is_fitted:
            raise ValueError("Scalers not fitted. Train model first.")
        
        # Transform features
        features = self.transform_features(df, fit=False)
        
        # Take last lookback_period samples
        if len(features) < self.lookback_period:
            # Pad if insufficient data
            padding = np.zeros((self.lookback_period - len(features), features.shape[1]))
            features = np.vstack([padding, features])
        
        # Create single sequence
        sequence = features[-self.lookback_period:]
        
        # Add batch dimension
        sequence = np.expand_dims(sequence, axis=0)
        
        logger.debug(f"Prepared inference sequence: shape {sequence.shape}")
        return sequence


def demo_feature_engineering():
    """Demo feature engineering pipeline."""
    from ..data import DataFetcher
    from ..indicators import TechnicalIndicators
    
    print("=" * 60)
    print("FEATURE ENGINEERING DEMO")
    print("=" * 60)
    
    # Fetch data
    fetcher = DataFetcher()
    fetcher.ensure_data_availability(min_records=2000)
    df = fetcher.get_latest_data(limit=2000)
    
    # Calculate indicators
    print("\n📊 Calculating technical indicators...")
    df = TechnicalIndicators.calculate_all_indicators(df)
    
    # Initialize feature engineer
    engineer = FeatureEngineer(lookback_period=60)
    
    # Prepare training data
    print("\n🔧 Preparing training data...")
    X_train, X_val, y_train, y_val = engineer.prepare_train_data(df)
    
    print(f"\n✓ Training set:")
    print(f"   X_train shape: {X_train.shape}")
    print(f"   y_train shape: {y_train.shape}")
    print(f"   Label distribution: UP={np.sum(y_train==1)}, "
          f"DOWN={np.sum(y_train==0)}, HOLD={np.sum(y_train==2)}")
    
    print(f"\n✓ Validation set:")
    print(f"   X_val shape: {X_val.shape}")
    print(f"   y_val shape: {y_val.shape}")
    
    # Prepare inference data
    print("\n🔮 Preparing inference sequence...")
    recent_df = df.tail(100)
    X_inference = engineer.prepare_inference_data(recent_df)
    print(f"   Inference shape: {X_inference.shape}")
    
    print("\n✅ Feature engineering demo complete!")


if __name__ == "__main__":
    demo_feature_engineering()
