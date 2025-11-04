from playwright.async_api import async_playwright

async def fetch_quiz_data(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        content = await page.content()
        await browser.close()
        return {"page_content": content}
