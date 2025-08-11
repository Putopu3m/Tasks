import asyncio
import json

import aiohttp

urls = [
    "https://jsonplaceholder.typicode.com/posts",
    "https://api.github.com/users/octocat",
    "https://dog.ceo/api/breeds/image/random",
    "https://hp-api.onrender.com/api/characters",
]  # Тестовые API


async def fetch_urls(urls: list[str], file_path: str):
    semaphore = asyncio.Semaphore(5)
    timeout = aiohttp.ClientTimeout(total=10)
    results = []

    async with aiohttp.ClientSession(timeout=timeout) as session:

        async def fetch_one(url: str) -> dict:
            async with semaphore:
                try:
                    async with session.get(url) as response:
                        status = response.status
                except Exception:
                    status = 0
                results.append({"url": url, "status": status})

        await asyncio.gather(*(fetch_one(url) for url in urls))

    with open(file_path, "w", encoding="utf-8") as f:
        for result in results:
            json.dump(result, f, ensure_ascii=False)
            f.write("\n")


if __name__ == "__main__":
    asyncio.run(fetch_urls(urls, "./results.jsonl"))
