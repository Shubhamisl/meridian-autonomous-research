from duckduckgo_search import DDGS
from src.meridian.domain.entities import Document

class WebSearchClient:
    async def search(self, query: str, limit: int = 5) -> list[Document]:
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=limit)]
            
            return [
                Document(
                    source="web",
                    title=r.get("title", ""),
                    content=r.get("body", ""),
                    url=r.get("href", ""),
                )
                for r in results
            ]
        except Exception:
            return []
