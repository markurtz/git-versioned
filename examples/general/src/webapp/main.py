# Copyright 2026 markurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Runnable server for the dynamic webapp example.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from webapp import __version__

__all__ = ["VersionHandler", "run_server"]


class VersionHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler serving application version endpoints.
    """

    def do_GET(self) -> None:
        """
        Handle incoming GET requests.
        """
        if self.path == "/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"version": __version__}
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Webapp versioned by GitVersioned</h1>")


def run_server(port: int = 8000) -> None:
    """
    Initialize and execute the HTTPServer loop.

    :param port: The target port to bind the server to.
    """
    server_address = ("", port)
    httpd = HTTPServer(server_address, VersionHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
