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
    """
    WSGI требует строку статуса вида '200 OK'.
    Берём reason-фразу из http.HTTPStatus, если она известна.
    """
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
    """
    Главная точка входа WSGI.
    Сервер (wsgiref, gunicorn, uWSGI и т.п.) вызывает её на каждый HTTP-запрос.

    environ: dict с данными запроса (метод, путь, заголовки и т.п.)
    start_response: функция для отправки статуса/заголовков; принимает (status_line, headers_list)
    Функция должна вернуть итерируемое из байтов (тело ответа).
    """
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    if path == "/favicon.ico":
        start_response(_http_status_line(204), [])
        return [b""]

    if method != "GET":
        return _error(start_response, 405, "Method Not Allowed (use GET)")

    # Ожидаем путь вида '/USD'
    # Уберём ведущие/хвостовые слеши и проверим, что это три буквы
    currency = path.strip("/")

    if not currency:
        return not_found(start_response)

    if not re.fullmatch(r"[A-Za-z]{3}", currency):
        return _bad_request(
            start_response, "Currency must be 3 latin letters, e.g. USD, EUR"
        )

    currency = currency.upper()

    # Формируем апстрим-URL к провайдеру
    upstream_url: str = f"https://api.exchangerate-api.com/v4/latest/{currency}"

    # Делаем исходящий HTTP-запрос стандартной библиотекой (без сторонних пакетов)
    req = urllib.request.Request(
        upstream_url,
        headers={
            "User-Agent": "wsgi-currency-proxy/1.0 (+https://www.python.org/)",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        # timeout защитит нас от вечно висящих соединений
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            # читаем сырое тело (это уже JSON от провайдера) — проксируем "как есть"
            body = resp.read()

            # Можно пробросить контент-тайп провайдера, но мы явно ставим JSON
            headers = [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                # Небольшая защита от кэширования прокси/браузером
                ("Cache-Control", "no-store"),
                # Немного CORS, чтобы было удобно тестировать из браузера
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Expose-Headers", "Content-Type"),
                # Опционально — сообщим клиенту, кто источник
                ("X-Proxy-Provider", PROVIDER),
            ]

            start_response(_http_status_line(status_code), headers)
            return [body]

    except urllib.error.HTTPError as e:
        # Провайдер вернул HTTP-ошибку (например, 404 для неизвестной валюты)
        # Проксируем его код и тело, если есть
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
        # Ошибка сети/DNS/SSL и т.п. — считаем, что апстрим недоступен
        return _error(start_response, 502, f"Bad Gateway: {e.reason}")

    except Exception as e:
        # Непредвиденная ошибка внутри нашего приложения
        return _error(start_response, 500, f"Internal Server Error: {e}")


# Небольшой dev-сервер из стандартной библиотеки.
# Это не для продакшена, но удобно для локального запуска.
if __name__ == "__main__":
    with make_server("127.0.0.1", 8000, app) as server:
        print("Serving on http://127.0.0.1:8000 (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
