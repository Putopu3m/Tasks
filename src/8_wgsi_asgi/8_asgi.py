# Запуск:
#   uvicorn 8_asgi:app --host 127.0.0.1 --port 8000
# Тест:
#   curl -i http://127.0.0.1:8000/USD

import asyncio
import json
import re

import aiohttp

PROVIDER = "https://www.exchangerate-api.com"


async def send_json_error(send, status: int, message: str):
    body = json.dumps({"error": message}).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
        (b"access-control-allow-origin", b"*"),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})


def parse_currency(path: str) -> str | None:
    currency = path.strip("/")
    if not re.fullmatch(r"[A-Za-z]{3}", currency or ""):
        return None
    return currency.upper()


async def app(scope, receive, send):
    if scope["type"] != "http":
        await send_json_error(send, 404, "Unsupported scope type")
        return

    method: str = scope.get("method", "GET").upper()
    path: str = scope.get("path", "/")

    if path == "/favicon.ico":
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        return

    if method not in ("GET", "HEAD"):
        await send_json_error(send, 405, "Method Not Allowed (use GET/HEAD)")
        return

    currency = parse_currency(path)
    if not currency:
        await send_json_error(send, 400, "Usage: GET /USD (3-letter currency code)")
        return

    upstream_url = f"https://api.exchangerate-api.com/v4/latest/{currency}"

    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                upstream_url, headers={"Accept": "application/json"}
            ) as resp:
                headers = [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"cache-control", b"no-store"),
                    (b"access-control-allow-origin", b"*"),
                    (b"x-proxy-provider", PROVIDER.encode("ascii")),
                ]

                await send(
                    {
                        "type": "http.response.start",
                        "status": resp.status,
                        "headers": headers,
                    }
                )

                if method == "HEAD":
                    await send(
                        {"type": "http.response.body", "body": b"", "more_body": False}
                    )
                    return

                async for chunk in resp.content.iter_chunked(64 * 1024):
                    await send(
                        {"type": "http.response.body", "body": chunk, "more_body": True}
                    )

                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False}
                )

    except asyncio.TimeoutError:
        await send_json_error(send, 504, "Upstream timeout")
    except aiohttp.ClientError as e:
        await send_json_error(send, 502, f"Bad Gateway: {e.__class__.__name__}")
    except Exception:
        await send_json_error(send, 500, "Internal Server Error")
