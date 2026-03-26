import logging
import os

import httpx

from src.meridian.domain.entities import Document

logger = logging.getLogger(__name__)


class IEEEClient:
    BASE_URL = "https://ieeexploreapi.ieee.org/api/v1/search/articles"

    async def search(self, query: str, limit: int = 3) -> list[Document]:
        api_key = os.getenv("IEEE_API_KEY")
        if not api_key:
            logger.warning("IEEE_API_KEY is missing; returning no IEEE results")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "apikey": api_key,
                        "querytext": query,
                        "max_records": limit,
                        "start_record": 1,
                        "sort_order": "desc",
                    },
                )
                response.raise_for_status()
                payload = response.json()

            articles = payload.get("articles") or payload.get("data") or payload.get("records") or []
            documents = []
            for article in articles[:limit]:
                documents.append(
                    Document(
                        source="ieee",
                        title=article.get("title", ""),
                        content=article.get("abstract", article.get("abstractText", "")),
                        url=article.get("html_url", article.get("pdf_url", article.get("pdfUrl", ""))),
                    )
                )
            return documents
        except Exception:
            return []
