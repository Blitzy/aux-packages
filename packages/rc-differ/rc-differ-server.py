#!/usr/bin/env python3
import sys
import os
import webbrowser
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket

# Global variables
file_data = {}
server_running = False
httpd = None
port = 8765

class DiffDataHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        global server_running, httpd
        
        self._set_headers()
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/diff-data':
            self.wfile.write(json.dumps(file_data).encode())
            print("Data sent to browser client successfully")
        elif path == '/shutdown':
            self.wfile.write(json.dumps({"status": "Shutting down server"}).encode())
            print("Shutdown request received. Shutting down server...")
            threading.Thread(target=self.shutdown_server, daemon=True).start()
        else:
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def shutdown_server(self):
        global server_running, httpd
        server_running = False
        if httpd:
            httpd.shutdown()

def start_http_server(port):
    """Start the HTTP server in a separate thread."""
    global server_running, httpd
    
    server_address = ('localhost', port)
    httpd = HTTPServer(server_address, DiffDataHandler)
    
    server_running = True
    print(f"HTTP server starting on port {port}")
    
    try:
        httpd.serve_forever()
    finally:
        print("Server has been shut down")

def is_port_in_use(port):
    """Check if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def update_file_data(original_file, modified_file):
    """Update the server's file data."""
    global file_data
    
    # Read the contents of both files
    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        original_content = f"Error reading {original_file}: {str(e)}"
    
    try:
        with open(modified_file, 'r', encoding='utf-8') as f:
            modified_content = f.read()
    except Exception as e:
        modified_content = f"Error reading {modified_file}: {str(e)}"
    
    # Update the data structure
    file_data.clear()  # Clear any existing data
    file_data.update({
        "original": original_content,
        "modified": modified_content,
        "originalName": os.path.basename(original_file),
        "modifiedName": os.path.basename(modified_file)
    })

def main():
    global server_running, httpd, port
    
    # Check if we have the correct number of arguments
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <original_file> <modified_file>")
        sys.exit(1)
    
    original_file = sys.argv[1]
    modified_file = sys.argv[2]
    
    # Update file data
    update_file_data(original_file, modified_file)
    
    # Check if the server is already running
    server_already_running = is_port_in_use(port)
    
    if not server_already_running:
        # Start HTTP server in a separate thread
        server_thread = threading.Thread(
            target=start_http_server,
            args=(port,),
            daemon=True
        )
        server_thread.start()
        
        # Small delay to ensure server starts before opening browser
        time.sleep(0.5)
    else:
        print(f"Server already running on port {port}, updated with new diff data")
    
    # Open the brandplayer URL with parameters to connect to our HTTP server
    base_url = "https://auxplayer.com"
    url = f"{base_url}?ask=rc-differ&staticInst=rc-differ-server&gridPortal=home&httpPort={port}"
    
    print(f"Opening diff viewer for {os.path.basename(original_file)} and {os.path.basename(modified_file)}")
    print(f"HTTP server running on: http://localhost:{port}")
    print(f"Opening URL: {url}")
    
    webbrowser.open(url)
    
    # Keep the script running to maintain the HTTP server if we just started it
    # The user can exit with Ctrl+C
    try:
        if not server_already_running:
            while server_running:
                time.sleep(1)
        else:
            print("File data updated. You can close this window if no other instances are running.")
    except KeyboardInterrupt:
        if not server_already_running:
            print("Shutting down HTTP server...")
            if httpd:
                httpd.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()