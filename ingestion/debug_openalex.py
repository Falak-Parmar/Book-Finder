import aiohttp
import asyncio
import os

async def debug():
    api_key = os.environ.get("OPENALEX_API_KEY")
    if not api_key:
        print("WARNING: OPENALEX_API_KEY not found in environment variables.")
    else:
        print("Found OPENALEX_API_KEY in environment.")

    url = "https://api.openalex.org/works"
    params = {
        'search': 'Network design',
        'per_page': 1,
        'mailto': 'falak.parmar.bookfinder.proj+test3@gmail.com'
    }
    headers = {}
    if api_key:
        headers['api_key'] = api_key

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            print(f"Status: {resp.status}")
            print(f"Headers: {resp.headers}")
            if resp.status != 200:
                print(await resp.text())
            else:
                data = await resp.json()
                print(f"Results: {len(data.get('results', []))}")  

if __name__ == "__main__":
    asyncio.run(debug())
