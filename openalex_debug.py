
import aiohttp
import asyncio
import json
import os

async def fetch_debug():
    title = "Software Testing in the Real World"
    author = "Edward Kit"
    base_url = "https://api.openalex.org/works"
    query = f"{title} {author}"
    params = {
        "search": query,
        "per-page": 1,
        "mailto": "antigravity_debug@example.com"
    }
    
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        params["api_key"] = key
        print("Using API Key")
    else:
        print("No API Key")

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(fetch_debug())
