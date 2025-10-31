"""
Quick Launch Script for Bitcoin Scalping Indicator Demo
This script launches the Streamlit dashboard demo.
"""

import subprocess
import sys
import os

def check_streamlit():
    """Check if Streamlit is installed."""
    try:
        import streamlit
        return True
    except ImportError:
        return False

def main():
    print("=" * 60)
    print("Bitcoin Scalping Indicator - Demo Launcher")
    print("=" * 60)
    print()
    
    if not check_streamlit():
        print("❌ Streamlit not found!")
        print("Installing Streamlit...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"])
    
    print("✅ Launching Streamlit dashboard...")
    print()
    print("📊 The app will open in your browser at: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    print("-" * 60)
    
    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "src/app.py",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ])
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped.")
    except Exception as e:
        print(f"\n❌ Error launching dashboard: {e}")
        print("\nTry running manually:")
        print("  streamlit run src/app.py")

if __name__ == "__main__":
    main()
