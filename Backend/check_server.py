#!/usr/bin/env python3
"""
Simple script to check if the FastAPI server is running and start it if needed.
"""
import requests
import subprocess
import sys
import time

def check_server_running():
    """Check if the server is running on localhost:8000"""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    try:
        # Start the server using uvicorn
        subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        print("⏳ Waiting for server to start...")
        time.sleep(3)
        
        if check_server_running():
            print("✅ Server started successfully!")
            return True
        else:
            print("❌ Server failed to start")
            return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def main():
    print("🔍 Checking if FastAPI server is running...")
    
    if check_server_running():
        print("✅ Server is already running on http://localhost:8000")
        return
    
    print("❌ Server is not running")
    
    if start_server():
        print("🎉 Server is now running and ready for requests!")
    else:
        print("💥 Failed to start the server. Please check the logs.")

if __name__ == "__main__":
    main()
