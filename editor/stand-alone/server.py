#!/usr/bin/env python3
"""Simple HTTP server for the ODWN LMF Editor.

Usage:
    python3 server.py          # serves on http://localhost:8080
    python3 server.py 9000     # custom port
"""
import http.server, sys, os

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map['.xml'] = 'application/xml'

print(f"ODWN LMF Editor running at http://localhost:{port}")
print(f"Serving from: {os.getcwd()}")
print("Press Ctrl+C to stop.\n")

with http.server.HTTPServer(('', port), handler) as httpd:
    httpd.serve_forever()
