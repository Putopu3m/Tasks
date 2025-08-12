import asyncio
import json

import aiofiles
import aiohttp
import ijson
from aiohttp import StreamReader 


async def fetch_and_parse(url: str, session: aiohttp.ClientSession):
    async def stream_json(stream: StreamReader):
        obj = {}
        async for prefix, event, value in ijson.parse_async(stream):
            if prefix == "" and event == "start_map":
                obj = {}
            elif event in ("string", "number", "boolean", "null"):
                obj[prefix] = value
            elif prefix == "" and event == "end_map":
                yield obj

    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = []
                async for item in stream_json(response.content):
                    content.append(item)
                return {"url": url, "content": content}
            else:
                return None
    except (asyncio.TimeoutError, aiohttp.ClientError):
        return None
    except Exception:
        return None


async def worker(
    name: int, queue: asyncio.Queue, output_file: str, session: aiohttp.ClientSession
):
    async with aiofiles.open(output_file, "a", encoding="utf-8") as out:
        while True:
            url = await queue.get()
            if url is None:  # сигнал остановки
                queue.task_done()
                break

            result = await fetch_and_parse(url, session)
            if result:
                await out.write(json.dumps(result, ensure_ascii=False) + "\n")

            queue.task_done()


async def fetch_urls(input_file: str, output_file: str, num_workers: int = 5):
    queue = asyncio.Queue()

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
        workers = [
            asyncio.create_task(worker(i, queue, output_file, session))
            for i in range(num_workers)
        ]

        async with aiofiles.open(input_file, "r", encoding="utf-8") as f:
            async for line in f:
                url = line.strip()
                if url:
                    await queue.put(url)

        await queue.join()

        for _ in range(num_workers):
            await queue.put(None)

        await asyncio.gather(*workers)


if __name__ == "__main__":
    asyncio.run(fetch_urls("urls.txt", "results.jsonl"))
