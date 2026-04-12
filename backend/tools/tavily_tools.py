import os
import logging
from tavily import AsyncTavilyClient
from typing import Any

logger = logging.getLogger(__name__)

class TavilyTools:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set - search will return mock data")
        self.client = None
    
    def _get_client(self):
        if self.client is None:
            try:
                self._client = AsyncTavilyClient(api_key=self.api_key)
            except ImportError:
                raise ImportError("Tavily not found")
        return self._client

    async def search(self, query: str, max_results: int = 3) -> list[dict]:
        if not self.api_key:
            return self._mock_results(query)
        
        try:
            client = self._get_client()
            response = await client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
                include_raw_content=False
            )
            results = []
            if response.get("answer"):
                results.append({
                    "title": "AI Answer",
                    "content": response["answer"],
                    "url": "",
                    "score": 1.0
                })
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                    "score": r.get("score", 0)
                })
            return results
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return self._mock_results(query)
    
    async def extract(self, url: str) -> str:
        """Extract clean content from a URL using Tavily Extract."""
        if not self.api_key:
            return f"[Mock extract for {url}]"

        try:
            client = self._get_client()
            response = await client.extract(urls=[url])
            results = response.get("results", [])
            if results:
                return results[0].get("raw_content", "")
            return ""
        except Exception as e:
            logger.error(f"Tavily extract error: {e}")
            return ""

    def _mock_results(self, query: str) -> list[dict]:
        """Mock results when API key is not configured."""
        return [
            {
                "title": f"Mock Result for: {query}",
                "content": f"This is a mock search result. Set TAVILY_API_KEY to enable real search. Query: {query}",
                "url": "https://example.com",
                "score": 0.9,
            }
        ]