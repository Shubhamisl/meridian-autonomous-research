import wikipedia
from pydantic import BaseModel

class WikipediaResult(BaseModel):
    title: str
    summary: str
    url: str

class WikipediaClient:
    async def search(self, query: str, limit: int = 3) -> list[WikipediaResult]:
        try:
            results = wikipedia.search(query, results=limit)
            docs = []
            for r in results:
                try:
                    page = wikipedia.page(r, auto_suggest=False)
                    docs.append(WikipediaResult(
                        title=page.title,
                        summary=page.summary[:1000],
                        url=page.url
                    ))
                except wikipedia.exceptions.DisambiguationError:
                    pass
                except wikipedia.exceptions.PageError:
                    pass
            return docs
        except Exception:
            return []
