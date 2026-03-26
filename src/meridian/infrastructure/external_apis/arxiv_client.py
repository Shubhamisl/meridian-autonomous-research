import arxiv
from pydantic import BaseModel

class ArXivResult(BaseModel):
    title: str
    summary: str
    url: str

class ArXivClient:
    async def search(self, query: str, limit: int = 3) -> list[ArXivResult]:
        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        client = arxiv.Client()
        results = []
        try:
            for r in client.results(search):
                results.append(ArXivResult(
                    title=r.title,
                    summary=r.summary,
                    url=r.pdf_url
                ))
            return results
        except Exception:
            return []
