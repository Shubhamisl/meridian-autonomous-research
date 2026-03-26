import types

import pytest

from src.meridian.domain.entities import Document


class FakeResponse:
    def __init__(self, text="", json_data=None):
        self.text = text
        self._json_data = json_data

    def json(self):
        return self._json_data

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, timeout=None):
        self.calls.append(("get", url, params))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_pubmed_returns_documents_from_mocked_api(monkeypatch):
    from src.meridian.infrastructure.external_apis.pubmed_client import PubMedClient

    esearch_xml = """
    <eSearchResult>
      <IdList>
        <Id>12345</Id>
      </IdList>
    </eSearchResult>
    """
    efetch_xml = """
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>12345</PMID>
              <Article>
                <ArticleTitle>PubMed Title</ArticleTitle>
                <Abstract>
                  <AbstractText>PubMed abstract text</AbstractText>
                </Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    client = FakeAsyncClient([FakeResponse(text=esearch_xml), FakeResponse(text=efetch_xml)])
    monkeypatch.setattr("src.meridian.infrastructure.external_apis.pubmed_client.httpx.AsyncClient", lambda: client)

    results = await PubMedClient().search("cancer")

    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].source == "pubmed"
    assert results[0].title == "PubMed Title"
    assert results[0].content == "PubMed abstract text"
    assert results[0].url == "https://pubmed.ncbi.nlm.nih.gov/12345/"


@pytest.mark.asyncio
async def test_ieee_returns_empty_list_and_logs_when_key_missing(monkeypatch, caplog):
    from src.meridian.infrastructure.external_apis.ieee_client import IEEEClient

    monkeypatch.delenv("IEEE_API_KEY", raising=False)

    results = await IEEEClient().search("distributed systems")

    assert results == []
    assert "IEEE_API_KEY" in caplog.text


@pytest.mark.asyncio
async def test_semantic_scholar_returns_documents_from_mocked_api(monkeypatch):
    from src.meridian.infrastructure.external_apis.semantic_scholar_client import SemanticScholarClient

    payload = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Semantic Scholar Title",
                "abstract": "Semantic Scholar abstract text",
                "url": "https://example.com/paper",
                "year": 2024,
                "authors": [{"name": "Ada Lovelace"}],
            }
        ]
    }
    client = FakeAsyncClient([FakeResponse(json_data=payload)])
    monkeypatch.setattr("src.meridian.infrastructure.external_apis.semantic_scholar_client.httpx.AsyncClient", lambda: client)

    results = await SemanticScholarClient().search("machine learning")

    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].source == "semantic_scholar"
    assert results[0].title == "Semantic Scholar Title"
    assert results[0].content == "Semantic Scholar abstract text"
    assert results[0].url == "https://example.com/paper"


@pytest.mark.asyncio
async def test_pubmed_returns_empty_list_on_fetch_failure(monkeypatch):
    from src.meridian.infrastructure.external_apis.pubmed_client import PubMedClient

    esearch_xml = """
    <eSearchResult>
      <IdList>
        <Id>12345</Id>
      </IdList>
    </eSearchResult>
    """
    client = FakeAsyncClient([FakeResponse(text=esearch_xml)])

    async def failing_get(url, params=None, timeout=None):
        raise RuntimeError("boom")

    client.get = failing_get
    monkeypatch.setattr("src.meridian.infrastructure.external_apis.pubmed_client.httpx.AsyncClient", lambda: client)

    results = await PubMedClient().search("cancer")

    assert results == []
