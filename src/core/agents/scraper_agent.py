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
    links: List[str] = []
    error: Optional[str] = None


class ScraperAgent:
    """Agent that scrapes web content and extracts relevant information."""

    def __init__(self):
        self.timeout = 10
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,it;q=0.8"
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
            # print(f"DEBUG: httpx.AsyncClient is {httpx.AsyncClient}")
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

            # Parse HTML
            soup = BeautifulSoup(text, 'lxml')

            # Extract title
            title = soup.title.string if soup.title else url
            
            # Extract links BEFORE decomposing tags
            from urllib.parse import urljoin, urlparse
            base_domain = urlparse(url).netloc
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)
                # Keep only internal links and ignore fragments/queries for simplicity
                if parsed.netloc == base_domain and parsed.scheme in ('http', 'https'):
                    links.add(full_url.split('#')[0])

            # Remove unnecessary tags
            for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'iframe', 'noscript']):
                tag.decompose()

            # Find main content
            main_content = None
            for selector in ['main', 'article', '[role="main"]', '.main-content', '#content', '.content', '.documentation', 'body']:
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

            # Convert to Markdown using markdownify
            from markdownify import markdownify
            markdown_text = markdownify(str(main_content), heading_style="ATX", strip=['a', 'img']) # Strip links/imgs for cleaner pure text
            
            # Clean up whitespace
            clean_text = "\n".join([line.strip() for line in markdown_text.splitlines() if line.strip()])

            # Truncate if too long
            if len(clean_text) > 20000:
                clean_text = clean_text[:20000] + "...[truncated]"

            return ScrapedContent(
                url=url,
                title=title, # .strip() might be good
                content=clean_text,
                links=list(links)
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

    async def crawl(self, start_url: str, max_depth: int = 1, max_pages: int = 5) -> List[ScrapedContent]:
        """Crawl a website recursively.

        Args:
            start_url: URL to start crawling from
            max_depth: Maximum recursion depth
            max_pages: Maximum total number of pages to scrape

        Returns:
            List of scraped content from visited pages
        """
        from urllib.parse import urlparse, urljoin
        import asyncio

        visited_urls = set()
        queue = [(start_url, 0)] # (url, depth)
        results = []
        
        domain = urlparse(start_url).netloc

        while queue and len(results) < max_pages:
            # Get next specific number of URLs to process concurrently
            # For simplicity, we process one batch (level) at a time or just pop?
            # Let's simple pop one for now, or batch properly. 
            # To go fast, let's grab up to 3 compatible tasks
            
            batch = []
            while queue and len(batch) < 3 and len(results) + len(batch) < max_pages:
                url, depth = queue.pop(0)
                if url in visited_urls:
                    continue
                visited_urls.add(url)
                batch.append((url, depth))

            if not batch:
                break

            # Scrape batch concurrently
            tasks = [self.scrape_url(url) for url, _ in batch]
            scraped_items = await asyncio.gather(*tasks, return_exceptions=True)

            for i, item in enumerate(scraped_items):
                url, depth = batch[i]
                
                if isinstance(item, Exception):
                    print(f"Error crawling {url}: {item}")
                    continue
                
                if item.error:
                     print(f"Skipping {url}: {item.error}")
                     continue

                results.append(item)
                print(f"✅ Crawled: {item.title} ({url})")

                # If we haven't reached max depth, find links
                if depth < max_depth:
                    try:
                        # Add new links to queue
                        new_links = item.links
                        for link in new_links:
                            if link not in visited_urls:
                                # Prioritize shorter URLs (likely higher in hierarchy) or just append
                                queue.append((link, depth + 1))
                                
                    except Exception as e:
                       print(f"Error extracting links from {url}: {e}")

        return results

    async def scrape_multiple(self, urls: List[str], max_urls: int = 3) -> List[ScrapedContent]:
        # Legacy support wrapper
        import asyncio
        tasks = [self.scrape_url(url) for url in urls[:max_urls]]
        return await asyncio.gather(*tasks)

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
