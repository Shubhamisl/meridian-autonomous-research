import wikipedia
from src.meridian.domain.entities import Document

class WikipediaClient:
    async def search(self, query: str, limit: int = 3) -> list[Document]:
        try:
            results = wikipedia.search(query, results=limit)
            docs = []
            for r in results:
                try:
                    page = wikipedia.page(r, auto_suggest=False)
                    docs.append(Document(
                        source="wikipedia",
                        title=page.title,
                        content=page.summary[:1000],
                        url=page.url,
                    ))
                except wikipedia.exceptions.DisambiguationError:
                    pass
                except wikipedia.exceptions.PageError:
                    pass
            return docs
        except Exception:
            return []
