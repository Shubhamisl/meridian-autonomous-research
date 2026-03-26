import httpx

from src.meridian.domain.entities import Document


class SemanticScholarClient:
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, limit: int = 5) -> list[Document]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "query": query,
                        "limit": limit,
                        "fields": "paperId,title,abstract,url,year,authors",
                    },
                )
                response.raise_for_status()
                payload = response.json()

            documents = []
            for paper in (payload.get("data") or [])[:limit]:
                documents.append(
                    Document(
                        source="semantic_scholar",
                        title=paper.get("title", ""),
                        content=paper.get("abstract", ""),
                        url=paper.get("url", "") or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                    )
                )
            return documents
        except Exception:
            return []
