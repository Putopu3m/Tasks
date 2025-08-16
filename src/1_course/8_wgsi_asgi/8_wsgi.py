# Запуск:
#   python wsgi_currency_proxy.py
# Тест:
#   curl -i http://127.0.0.1:8000/USD

import json
import re
import urllib.error
import urllib.request
from http import HTTPStatus
from wsgiref.simple_server import make_server

PROVIDER = "https://www.exchangerate-api.com"


def _http_status_line(status_code: int) -> str:
    try:
        reason = HTTPStatus(status_code).phrase
    except Exception:
        reason = "OK"
    return f"{status_code} {reason}"


def _bad_request(start_response, message: str):
    body = json.dumps({"error": message}).encode("utf-8")
    start_response(
        _http_status_line(400),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def not_found(start_response, message: str = "Not found"):
    body = json.dumps({"error": message}).encode("utf-8")
    start_response(
        _http_status_line(404),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _error(start_response, status: int, message: str):
    body = json.dumps({"error": message}).encode("utf-8")
    start_response(
        _http_status_line(status),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    if path == "/favicon.ico":
        start_response(_http_status_line(204), [])
        return [b""]

    if method != "GET":
        return _error(start_response, 405, "Method Not Allowed (use GET)")

    currency = path.strip("/")

    if not currency:
        return not_found(start_response)

    if not re.fullmatch(r"[A-Za-z]{3}", currency):
        return _bad_request(
            start_response, "Currency must be 3 latin letters, e.g. USD, EUR"
        )

    currency = currency.upper()

    upstream_url: str = f"https://api.exchangerate-api.com/v4/latest/{currency}"

    req = urllib.request.Request(
        upstream_url,
        headers={
            "User-Agent": "wsgi-currency-proxy/1.0 (+https://www.python.org/)",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            body = resp.read()

            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Expose-Headers", "Content-Type"),
                ("X-Proxy-Provider", PROVIDER),
            ]

            start_response(_http_status_line(status_code), headers)
            return [body]

    except urllib.error.HTTPError as e:
        err_body = e.read() or json.dumps(
            {"error": f"Upstream HTTPError: {e.code}"}
        ).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(err_body))),
            ("Cache-Control", "no-store"),
            ("X-Proxy-Provider", PROVIDER),
        ]
        start_response(_http_status_line(e.code), headers)
        return [err_body]

    except urllib.error.URLError as e:
        return _error(start_response, 502, f"Bad Gateway: {e.reason}")

    except Exception as e:
        return _error(start_response, 500, f"Internal Server Error: {e}")

if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, app) as server:
        print("Serving on http://127.0.0.1:8000 (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
