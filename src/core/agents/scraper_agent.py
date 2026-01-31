"""Scraper Agent - Scrapes and extracts content from web pages."""

from typing import List, Optional
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from src.core.llm.ollama_client import get_llm


class ScrapedContent(BaseModel):
    """Scraped content from a URL."""
    url: str
    title: str
    content: str
    error: Optional[str] = None


class ScraperAgent:
    """Agent that scrapes web content and extracts relevant information."""

    def __init__(self):
        self.timeout = 10
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MaskAgent/1.0"
        }

    async def scrape_url(self, url: str) -> ScrapedContent:
        """Scrape content from a single URL.

        Args:
            url: URL to scrape

        Returns:
            Scraped content or error
        """
        text = ""
        try:
            print(f"DEBUG: httpx.AsyncClient is {httpx.AsyncClient}")
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text

            if not text:
                 return ScrapedContent(
                    url=url,
                    title="Error",
                    content="",
                    error="No content received"
                )

            # Parse HTML (outside async with)
            soup = BeautifulSoup(text, 'lxml')

            # Extract title
            title = soup.title.string if soup.title else url

            # Remove unnecessary tags
            for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'iframe']):
                tag.decompose()

            # Find main content
            main_content = None
            for selector in ['main', 'article', '[role="main"]', '.main-content', '#content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.body

            if not main_content:
                return ScrapedContent(
                    url=url,
                    title=title,
                    content="",
                    error="Could not find content"
                )

            # Extract and clean text
            extracted_text = main_content.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
            clean_text = '\n'.join(lines)

            # Truncate if too long
            if len(clean_text) > 10000:
                clean_text = clean_text[:10000] + "...[truncated]"

            return ScrapedContent(
                url=url,
                title=title,
                content=clean_text
            )

        except httpx.HTTPStatusError as e:
            return ScrapedContent(
                url=url,
                title="Error",
                content="",
                error=f"HTTP {e.response.status_code}"
            )
        except httpx.TimeoutException:
            return ScrapedContent(
                url=url,
                title="Error",
                content="",
                error="Timeout"
            )
        except Exception as e:
            return ScrapedContent(
                url=url,
                title="Error",
                content="",
                error=str(e)
            )

    async def scrape_multiple(self, urls: List[str], max_urls: int = 3) -> List[ScrapedContent]:
        """Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            max_urls: Maximum number of URLs to scrape

        Returns:
            List of scraped content
        """
        import asyncio

        # Limit number of URLs
        urls_to_scrape = urls[:max_urls]

        # Scrape concurrently
        tasks = [self.scrape_url(url) for url in urls_to_scrape]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        scraped = []
        for result in results:
            if isinstance(result, ScrapedContent) and not result.error:
                scraped.append(result)
            elif isinstance(result, Exception):
                print(f"Scraping error: {result}")

        return scraped

    async def extract_relevant_content(self, scraped: ScrapedContent, query: str) -> str:
        """Extract only relevant parts using LLM.

        Args:
            scraped: Scraped content
            query: Original user query

        Returns:
            Relevant summary
        """
        if scraped.error or not scraped.content:
            return ""

        llm = await get_llm()

        prompt = f"""Extract and summarize ONLY the information relevant to this question from the article.

Question: "{query}"

Article Title: {scraped.title}
Article Content:
{scraped.content[:3000]}

Instructions:
- Extract only facts relevant to the question
- Keep it concise (2-4 paragraphs max)
- Include key details and numbers
- CRITICAL: If the article content does NOT contain any information directly relevant to the question, you MUST return exactly: "No relevant information found"
- Do NOT try to summarize the article if it's off-topic.

Relevant summary:"""

        try:
            response_msg = await llm.chat([
                {"role": "system", "content": "You are an expert at extracting relevant information from articles."},
                {"role": "user", "content": prompt}
            ])

            return response_msg.get("content", "").strip()
        except Exception as e:
            print(f"Error extracting relevant content: {e}")
            # Return truncated raw content as fallback
            return scraped.content[:1000]


# Singleton instance
_scraper_agent = None

async def get_scraper_agent() -> ScraperAgent:
    """Get singleton scraper agent instance."""
    global _scraper_agent
    if _scraper_agent is None:
        _scraper_agent = ScraperAgent()
    return _scraper_agent
