#!/usr/bin/env python3
"""
Simple development server for County Health Explorer frontend
Serves static files and proxies API requests to backend
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
from pathlib import Path

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
    """Start the development server"""
    port = 3000
    
    # Check if frontend directory exists
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        print("Make sure you're running this from the project root.")
        return
    
    print(f"🚀 Starting County Health Explorer development server...")
    print(f"📁 Serving files from: {frontend_dir.absolute()}")
    print(f"🌐 Frontend URL: http://localhost:{port}")
    print(f"🔗 Backend API: http://localhost:8000/api")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    
    try:
        with socketserver.TCPServer(("", port), ProxyHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {port} is already in use")
            print("Try stopping other servers or use a different port")
        else:
            print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main() 