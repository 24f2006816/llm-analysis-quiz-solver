import time
from app.scraper import fetch_quiz_data
from app.utils import submit_answer

async def solve_quiz_chain(url: str, email: str, secret: str):
    start = time.time()
    current_url = url
    results = []

    while current_url and time.time() - start < 180:
        quiz_data = await fetch_quiz_data(current_url)
        # TODO: Put logic to analyze the question and compute answer
        answer = "TODO"

        response = await submit_answer(current_url, answer, email, secret)
        results.append(response)

        if not response.get("url"):
            break
        current_url = response["url"]

    return results
