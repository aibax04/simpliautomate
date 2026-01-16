import subprocess
import time
import sys
import os

def run():
    print("--- SIMPLII: NEWS TO LINKEDIN AUTOMATION ---")
    print("Checking environment...")
    
    
    if not os.path.exists(".env"):
        print("Error: .env file missing. Create one with your API keys.")
        return

    
    print("Launching agents and server via Uvicorn...")
    try:
        
        cmd = [sys.executable, "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Failed to start: {e}")

if __name__ == "__main__":
    run()
