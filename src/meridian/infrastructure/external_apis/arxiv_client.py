import arxiv
from src.meridian.domain.entities import Document

class ArXivClient:
    async def search(self, query: str, limit: int = 3) -> list[Document]:
        try:
            search = arxiv.Search(
                query=query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance
            )

            client = arxiv.Client()
            return [
                Document(
                    source="arxiv",
                    title=r.title,
                    content=r.summary,
                    url=r.pdf_url,
                )
                for r in client.results(search)
            ]
        except Exception:
            return []
