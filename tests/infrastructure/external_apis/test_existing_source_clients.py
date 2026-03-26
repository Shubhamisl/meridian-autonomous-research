import sys
import types

import pytest

from src.meridian.domain.entities import Document

arxiv_stub = types.ModuleType("arxiv")


class _SortCriterion:
    Relevance = object()


class _Search:
    def __init__(self, query, max_results, sort_by):
        self.query = query
        self.max_results = max_results
        self.sort_by = sort_by


class _ArxivClientStub:
    def results(self, search):
        return iter([])


arxiv_stub.SortCriterion = _SortCriterion
arxiv_stub.Search = _Search
arxiv_stub.Client = lambda: _ArxivClientStub()
sys.modules.setdefault("arxiv", arxiv_stub)

wikipedia_stub = types.ModuleType("wikipedia")
wikipedia_stub.search = lambda query, results: []
wikipedia_stub.page = lambda title, auto_suggest=False: None
wikipedia_stub.exceptions = types.SimpleNamespace(
    DisambiguationError=Exception,
    PageError=Exception,
)
sys.modules.setdefault("wikipedia", wikipedia_stub)

duckduckgo_search_stub = types.ModuleType("duckduckgo_search")


class _DDGS:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, max_results):
        return []


duckduckgo_search_stub.DDGS = _DDGS
sys.modules.setdefault("duckduckgo_search", duckduckgo_search_stub)

from src.meridian.infrastructure.external_apis.arxiv_client import ArXivClient
from src.meridian.infrastructure.external_apis.web_search_client import WebSearchClient
from src.meridian.infrastructure.external_apis.wikipedia_client import WikipediaClient


@pytest.mark.asyncio
async def test_arxiv_client_returns_documents(monkeypatch):
    class FakeResult:
        title = "ArXiv Title"
        summary = "ArXiv summary text"
        pdf_url = "https://arxiv.org/pdf/1234.5678.pdf"

    class FakeClient:
        def results(self, search):
            return iter([FakeResult()])

    monkeypatch.setattr("src.meridian.infrastructure.external_apis.arxiv_client.arxiv.Client", lambda: FakeClient())

    client = ArXivClient()
    results = await client.search("quantum")

    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].source == "arxiv"
    assert results[0].title == "ArXiv Title"
    assert results[0].content == "ArXiv summary text"
    assert results[0].url == "https://arxiv.org/pdf/1234.5678.pdf"


@pytest.mark.asyncio
async def test_arxiv_client_swallows_search_construction_errors(monkeypatch):
    monkeypatch.setattr(
        "src.meridian.infrastructure.external_apis.arxiv_client.arxiv.Search",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    client = ArXivClient()
    results = await client.search("quantum")

    assert results == []


@pytest.mark.asyncio
async def test_wikipedia_client_returns_documents(monkeypatch):
    class FakePage:
        title = "Wikipedia Title"
        summary = "Wikipedia summary text" + ("x" * 1200)
        url = "https://en.wikipedia.org/wiki/Fake"

    monkeypatch.setattr(
        "src.meridian.infrastructure.external_apis.wikipedia_client.wikipedia.search",
        lambda query, results: ["Fake Page"],
    )
    monkeypatch.setattr(
        "src.meridian.infrastructure.external_apis.wikipedia_client.wikipedia.page",
        lambda title, auto_suggest=False: FakePage(),
    )

    client = WikipediaClient()
    results = await client.search("physics")

    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].source == "wikipedia"
    assert results[0].title == "Wikipedia Title"
    assert len(results[0].content) == 1000
    assert results[0].content == FakePage.summary[:1000]
    assert results[0].url == "https://en.wikipedia.org/wiki/Fake"


@pytest.mark.asyncio
async def test_web_search_client_returns_documents(monkeypatch):
    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def text(self, query, max_results):
            return [
                {
                    "title": "Web Title",
                    "body": "Web body text",
                    "href": "https://example.com/article",
                }
            ]

    monkeypatch.setattr("src.meridian.infrastructure.external_apis.web_search_client.DDGS", FakeDDGS)

    client = WebSearchClient()
    results = await client.search("news")

    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert results[0].source == "web"
    assert results[0].title == "Web Title"
    assert results[0].content == "Web body text"
    assert results[0].url == "https://example.com/article"
