#!/usr/bin/env python3
"""
Fix WebSocket installation and test
"""
import subprocess
import sys

def run_command(cmd):
    """Run command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔧 Fixing WebSocket installation...")
    
    # Uninstall and reinstall uvicorn with standard extras
    commands = [
        "pip uninstall -y uvicorn",
        "pip install 'uvicorn[standard]==0.24.0'",
        "pip install websockets",
        "pip install wsproto"
    ]
    
    for cmd in commands:
        print(f"\n📦 Running: {cmd}")
        success, stdout, stderr = run_command(cmd)
        if success:
            print(f"✅ Success")
        else:
            print(f"❌ Failed: {stderr}")
    
    # Test imports
    print("\n🧪 Testing imports...")
    try:
        import uvicorn
        print(f"✅ uvicorn: {uvicorn.__version__}")
    except ImportError as e:
        print(f"❌ uvicorn import failed: {e}")
    
    try:
        import websockets
        print(f"✅ websockets: {websockets.__version__}")
    except ImportError as e:
        print(f"❌ websockets import failed: {e}")
    
    try:
        import wsproto
        print(f"✅ wsproto: {wsproto.__version__}")
    except ImportError as e:
        print(f"❌ wsproto import failed: {e}")
    
    print("\n🚀 Now restart your server with: python run.py")

if __name__ == "__main__":
    main()