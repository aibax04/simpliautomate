import subprocess
import time
import sys
import os

def run():
    print("--- SIMPLII: NEWS TO LINKEDIN AUTOMATION ---")
    print("Checking environment...")
    
    # 1. Install requirements if needed (optional check)
    # subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])

    # 2. Check for .env
    if not os.path.exists(".env"):
        print("Error: .env file missing. Create one with your API keys.")
        return

    # 3. Start Backend
    print("Launching agents and server via Uvicorn...")
    try:
        # 3. Start Backend via Uvicorn directly
        # Use python -m uvicorn which is safer than relying on PATH
        cmd = [sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Failed to start: {e}")

if __name__ == "__main__":
    run()
