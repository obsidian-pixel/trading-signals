"""
Installation Verification Script
Checks that all dependencies are correctly installed and configured.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check Python version is compatible."""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 9:
        return True
    print("  ⚠️  Warning: Python 3.9+ recommended")
    return False

def check_dependencies():
    """Check all required packages are installed."""
    packages = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'talib': 'TA-Lib',
        'tensorflow': 'TensorFlow',
        'sklearn': 'scikit-learn',
        'xgboost': 'XGBoost',
        'optuna': 'Optuna',
        'streamlit': 'Streamlit',
        'plotly': 'Plotly',
        'binance': 'python-binance',
        'aiohttp': 'aiohttp',
        'dotenv': 'python-dotenv',
        'yaml': 'PyYAML',
    }
    
    all_ok = True
    for module, name in packages.items():
        try:
            if module == 'sklearn':
                import sklearn
                version = sklearn.__version__
            elif module == 'binance':
                from binance import Client
                version = "✓"
            elif module == 'dotenv':
                import dotenv
                version = "✓"
            elif module == 'yaml':
                import yaml
                version = "✓"
            else:
                mod = __import__(module)
                version = mod.__version__
            
            print(f"✓ {name}: {version}")
        except ImportError:
            print(f"✗ {name}: NOT INSTALLED")
            all_ok = False
    
    return all_ok

def check_directories():
    """Check required directories exist."""
    base_dir = Path(__file__).parent
    dirs = [
        'data/historical',
        'data/signals',
        'models',
        'logs',
        'config',
        'src/data',
        'src/indicators',
        'src/models',
        'src/strategies',
        'src/ui',
        'src/utils',
    ]
    
    all_ok = True
    for dir_path in dirs:
        full_path = base_dir / dir_path
        if full_path.exists():
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ - MISSING")
            all_ok = False
    
    return all_ok

def check_config_files():
    """Check configuration files exist."""
    base_dir = Path(__file__).parent
    files = [
        '.env',
        'requirements.txt',
        'config/model_params.yaml',
        'config/strategy_params.yaml',
    ]
    
    all_ok = True
    for file_path in files:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            all_ok = False
    
    return all_ok

def test_talib():
    """Test TA-Lib functionality."""
    try:
        import talib
        import numpy as np
        
        # Test RSI calculation
        data = np.random.random(100)
        rsi = talib.RSI(data, timeperiod=14)
        print(f"✓ TA-Lib RSI test passed")
        return True
    except Exception as e:
        print(f"✗ TA-Lib test failed: {e}")
        return False

def test_tensorflow():
    """Test TensorFlow functionality."""
    try:
        import tensorflow as tf
        
        # Suppress TF warnings
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        
        # Simple tensor operation
        a = tf.constant([[1, 2], [3, 4]])
        b = tf.constant([[5, 6], [7, 8]])
        c = tf.matmul(a, b)
        
        print(f"✓ TensorFlow test passed (GPU: {len(tf.config.list_physical_devices('GPU')) > 0})")
        return True
    except Exception as e:
        print(f"✗ TensorFlow test failed: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Bitcoin Scalping Indicator - Installation Verification")
    print("=" * 60)
    
    print("\n📌 Python Version:")
    python_ok = check_python_version()
    
    print("\n📦 Package Dependencies:")
    packages_ok = check_dependencies()
    
    print("\n📁 Directory Structure:")
    dirs_ok = check_directories()
    
    print("\n📄 Configuration Files:")
    config_ok = check_config_files()
    
    print("\n🧪 Functionality Tests:")
    talib_ok = test_talib()
    tf_ok = test_tensorflow()
    
    print("\n" + "=" * 60)
    if all([python_ok, packages_ok, dirs_ok, config_ok, talib_ok, tf_ok]):
        print("✅ ALL CHECKS PASSED - Installation successful!")
        print("\nNext steps:")
        print("  1. Review .env configuration")
        print("  2. Fetch historical data: python -m src.data.data_fetcher")
        print("  3. Train models: python -m src.train_models")
        print("  4. Run dashboard: streamlit run src/app.py")
    else:
        print("⚠️  SOME CHECKS FAILED - Please review errors above")
        return 1
    
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
