from duckduckgo_search import DDGS
from pydantic import BaseModel

class WebSearchResult(BaseModel):
    title: str
    body: str
    url: str

class WebSearchClient:
    async def search(self, query: str, limit: int = 5) -> list[WebSearchResult]:
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=limit)]
            
            return [
                WebSearchResult(title=r.get("title", ""), body=r.get("body", ""), url=r.get("href", ""))
                for r in results
            ]
        except Exception:
            return []
