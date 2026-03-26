import xml.etree.ElementTree as ET

import httpx

from src.meridian.domain.entities import Document


class PubMedClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    async def search(self, query: str, limit: int = 3) -> list[Document]:
        try:
            async with httpx.AsyncClient() as client:
                esearch_response = await client.get(
                    f"{self.BASE_URL}esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": limit,
                        "retmode": "xml",
                    },
                )
                esearch_response.raise_for_status()

                pmids = self._extract_pmids(esearch_response.text)[:limit]
                if not pmids:
                    return []

                efetch_response = await client.get(
                    f"{self.BASE_URL}efetch.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "rettype": "abstract",
                        "retmode": "xml",
                    },
                )
                efetch_response.raise_for_status()

                return self._extract_documents(efetch_response.text)[:limit]
        except Exception:
            return []

    def _extract_pmids(self, xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text)
        return [node.text for node in root.findall(".//Id") if node.text]

    def _extract_documents(self, xml_text: str) -> list[Document]:
        root = ET.fromstring(xml_text)
        documents = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//MedlineCitation/PMID", default="").strip()
            title = article.findtext(".//ArticleTitle", default="").strip()
            abstract_parts = [
                part.text.strip()
                for part in article.findall(".//Abstract/AbstractText")
                if part.text and part.text.strip()
            ]
            content = "\n".join(abstract_parts)
            if pmid:
                documents.append(
                    Document(
                        source="pubmed",
                        title=title,
                        content=content,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    )
                )
        return documents
