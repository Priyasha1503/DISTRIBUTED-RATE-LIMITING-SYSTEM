import asyncio
import httpx
import time

async def send_request(client, i):
    url = "http://127.0.0.1:8000/api/data"
    try:
        response = await client.get(url)
        print(f"Request {i}: Status {response.status_code} - {response.json().get('message', 'Blocked')}")
    except Exception as e:
        print(f"Error on request {i}: {e}")

async def run_test():
    async with httpx.AsyncClient() as client:
        # We send 15 requests as fast as possible
        # Since our limit is 5 per minute, 10 should fail!
        tasks = [send_request(client, i) for i in range(1, 16)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    print("🚀 STARTING STRESS TEST...")
    start_time = time.time()
    asyncio.run(run_test())
    print(f"🏁 Finished in {time.time() - start_time:.2f} seconds")