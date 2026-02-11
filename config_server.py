"""
Simple config server to securely serve Supabase credentials to the frontend.
Reads from environment variables, returns only the necessary public config.
"""

import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()


class ConfigHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for config."""
        if self.path == "/api/config":
            if not SUPABASE_URL or not SUPABASE_ANON_KEY:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response = {"error": "Supabase credentials not configured"}
                self.wfile.write(json.dumps(response).encode())
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            response = {
                "supabaseUrl": SUPABASE_URL,
                "supabaseAnonKey": SUPABASE_ANON_KEY
            }
            self.wfile.write(json.dumps(response).encode())
            return

        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Config server running. Access /api/config for Supabase config.\n")
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        logger.info(format % args)


def main():
    port = int(os.environ.get("CONFIG_SERVER_PORT", 8080))
    server = HTTPServer(("127.0.0.1", port), ConfigHandler)
    logger.info(f"Config server listening on http://127.0.0.1:{port}")
    logger.info("Set SUPABASE_URL and SUPABASE_ANON_KEY env vars before running")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down config server")
        server.shutdown()


if __name__ == "__main__":
    main()
