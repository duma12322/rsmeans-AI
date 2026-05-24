from crawl4ai import AsyncWebCrawler


async def extract_content(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        return result.markdown