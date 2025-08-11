import asyncio
import json

import aiofiles
import aiohttp
import ijson
from aiohttp import StreamReader


async def fetch_urls(input_file: str, output_file: str):
    semaphore = asyncio.Semaphore(5)

    async def fetch_and_parse(url: str):
        async def stream_json(stream: StreamReader):
            obj = {}
            async for prefix, event, value in ijson.parse_async(stream):
                if prefix == "" and event == "start_map":
                    obj = {}
                elif event in ("string", "number", "boolean", "null"):
                    obj[prefix] = value
                elif prefix == "" and event == "end_map":
                    yield obj

        async with semaphore:
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(10)
                ) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = []
                            async for item in stream_json(response.content):
                                content.append(item)
                            return {"url": url, "content": content}
                        else:
                            return None

            except asyncio.TimeoutError:
                return None

            except aiohttp.ClientError:
                return None

            except Exception:
                return None

    async with aiofiles.open(input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in await f.readlines() if line.strip()]

    async with aiofiles.open(output_file, "w", encoding="utf-8") as out:
        for coroutine in asyncio.as_completed(fetch_and_parse(url) for url in urls):
            result = await coroutine
            if result:
                await out.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    asyncio.run(fetch_urls("urls.txt", "results.jsonl"))
