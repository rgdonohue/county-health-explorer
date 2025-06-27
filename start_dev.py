#!/usr/bin/env python3
"""
Development startup script for County Health Explorer
Starts both backend and frontend servers with proper coordination
"""

import subprocess
import time
import sys
import signal
import os
from pathlib import Path

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n👋 Shutting down servers...')
    sys.exit(0)

def main():
    """Start both backend and frontend development servers"""
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("frontend").exists():
        print("❌ Please run this script from the project root directory")
        print("Expected directories: backend/, frontend/")
        return
    
    print("🏥 County Health Explorer - Development Environment")
    print("=" * 60)
    print("Starting both backend and frontend servers...")
    print()
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    processes = []
    
    try:
        # Start backend server
        print("🔧 Starting backend server...")
        backend_cmd = [
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--port", "8000",
            "--host", "127.0.0.1"
        ]
        
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(("Backend", backend_process))
        
        # Wait a moment for backend to start
        print("⏳ Waiting for backend to initialize...")
        time.sleep(3)
        
        # Check if backend started successfully
        if backend_process.poll() is not None:
            print("❌ Backend server failed to start")
            return
        
        print("✅ Backend server started at http://localhost:8000")
        print("📚 API Documentation: http://localhost:8000/docs")
        print()
        
        # Start frontend server
        print("🌐 Starting frontend server...")
        frontend_process = subprocess.Popen(
            [sys.executable, "serve_frontend.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(("Frontend", frontend_process))
        
        # Wait a moment for frontend to start
        time.sleep(2)
        
        # Check if frontend started successfully
        if frontend_process.poll() is not None:
            print("❌ Frontend server failed to start")
            return
        
        print("✅ Frontend server started at http://localhost:3000")
        print()
        print("🎉 Both servers are running!")
        print("=" * 60)
        print("🌐 Open your browser to: http://localhost:3000")
        print("📚 API Documentation: http://localhost:8000/docs")
        print("Press Ctrl+C to stop both servers")
        print("=" * 60)
        
        # Keep the script running and monitor processes
        while True:
            time.sleep(1)
            
            # Check if any process has died
            for name, process in processes:
                if process.poll() is not None:
                    print(f"❌ {name} server has stopped unexpectedly")
                    return
                    
    except KeyboardInterrupt:
        print("\n👋 Shutting down servers...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up processes
        for name, process in processes:
            if process.poll() is None:
                print(f"🛑 Stopping {name} server...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        print("✅ All servers stopped")

if __name__ == "__main__":
    main() 