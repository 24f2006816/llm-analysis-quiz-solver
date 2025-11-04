import aiohttp

async def submit_answer(url, answer, email, secret):
    async with aiohttp.ClientSession() as session:
        payload = {
            "email": email,
            "secret": secret,
            "url": url,
            "answer": answer
        }
        async with session.post(url, json=payload) as res:
            try:
                return await res.json()
            except:
                return {"error": "Invalid response"}
