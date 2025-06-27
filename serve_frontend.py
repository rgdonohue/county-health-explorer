#!/usr/bin/env python3
"""
Simple development server for County Health Explorer frontend
Serves static files and proxies API requests to backend
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import json
import time
from pathlib import Path

def check_backend_health(backend_url="http://localhost:8000", timeout=5):
    """
    Check if the backend server is running and healthy
    
    Args:
        backend_url: URL of the backend server
        timeout: Timeout in seconds for the health check
        
    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    try:
        # Try to connect to the backend health endpoint
        health_url = f"{backend_url}/docs"  # FastAPI docs endpoint is always available
        
        request = urllib.request.Request(health_url)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.getcode() == 200:
                return True, f"✅ Backend server is running at {backend_url}"
            else:
                return False, f"❌ Backend server responded with status {response.getcode()}"
                
    except urllib.error.URLError as e:
        if hasattr(e, 'reason'):
            if "Connection refused" in str(e.reason):
                return False, f"❌ Backend server is not running at {backend_url}"
            else:
                return False, f"❌ Cannot reach backend server: {e.reason}"
        else:
            return False, f"❌ Backend server error: {e}"
    except Exception as e:
        return False, f"❌ Unexpected error checking backend: {e}"

def wait_for_backend(backend_url="http://localhost:8000", max_wait=30):
    """
    Wait for backend to become available with a timeout
    
    Args:
        backend_url: URL of the backend server
        max_wait: Maximum time to wait in seconds
        
    Returns:
        bool: True if backend becomes available, False if timeout
    """
    print(f"⏳ Waiting for backend server at {backend_url}...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        is_healthy, message = check_backend_health(backend_url, timeout=2)
        if is_healthy:
            print(message)
            return True
        
        print(".", end="", flush=True)
        time.sleep(1)
    
    print(f"\n❌ Timeout: Backend server did not start within {max_wait} seconds")
    return False

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that proxies API calls to the backend"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        super().__init__(*args, directory="frontend", **kwargs)
    
    def do_GET(self):
        """Handle GET requests - proxy API calls, serve static files otherwise"""
        
        # Check if this is an API request
        if self.path.startswith('/api/'):
            self.proxy_api_request()
        else:
            # Serve static files
            super().do_GET()
    
    def proxy_api_request(self):
        """Proxy API requests to the backend server"""
        backend_url = f"http://localhost:8000{self.path}"
        
        try:
            # Make request to backend
            response = urllib.request.urlopen(backend_url)
            data = response.read()
            
            # Set response headers
            self.send_response(response.getcode())
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Send response data
            self.wfile.write(data)
            
        except urllib.error.HTTPError as e:
            # Handle HTTP errors
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": f"Backend error: {e.reason}",
                "status": e.code
            }
            self.wfile.write(json.dumps(error_response).encode())
            
        except Exception as e:
            # Handle other errors
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": f"Proxy error: {str(e)}",
                "status": 500
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    """Start the development server with backend health check"""
    port = 3000
    backend_url = "http://localhost:8000"
    
    # Check if frontend directory exists
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        print("Make sure you're running this from the project root.")
        return
    
    print("🏥 County Health Explorer - Development Server")
    print("=" * 50)
    
    # Check if backend is running
    print("🔍 Checking backend server status...")
    is_healthy, health_message = check_backend_health(backend_url)
    
    if not is_healthy:
        print(health_message)
        print()
        print("💡 To start the backend server, run:")
        print("   cd backend && uvicorn app.main:app --reload --port 8000")
        print()
        
        # Ask user if they want to wait for backend
        try:
            user_input = input("Would you like to wait for the backend to start? (y/N): ").strip().lower()
            if user_input in ['y', 'yes']:
                if not wait_for_backend(backend_url, max_wait=60):
                    print("❌ Cannot start frontend without backend server")
                    return
            else:
                print("❌ Cannot start frontend without backend server")
                return
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            return
    else:
        print(health_message)
    
    print()
    print(f"🚀 Starting County Health Explorer frontend server...")
    print(f"📁 Serving files from: {frontend_dir.absolute()}")
    print(f"🌐 Frontend URL: http://localhost:{port}")
    print(f"🔗 Backend API: {backend_url}/api")
    print(f"📚 API Docs: {backend_url}/docs")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", port), ProxyHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Frontend server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {port} is already in use")
            print("Try stopping other servers or use a different port")
        else:
            print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main() 