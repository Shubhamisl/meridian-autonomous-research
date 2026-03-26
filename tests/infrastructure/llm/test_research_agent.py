import sys
import types

import pytest

from src.meridian.domain.entities import Document

arxiv_stub = types.ModuleType("arxiv")
arxiv_stub.SortCriterion = types.SimpleNamespace(Relevance=object())
arxiv_stub.Search = lambda *args, **kwargs: object()
arxiv_stub.Client = lambda: object()
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
duckduckgo_search_stub.DDGS = lambda: object()
sys.modules.setdefault("duckduckgo_search", duckduckgo_search_stub)

from src.meridian.infrastructure.llm.research_agent import ResearchAgent


class FakeToolFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = FakeToolFunction(name, arguments)


class FakeResponse:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls

    def model_dump(self, exclude_unset=True):
        return {"role": "assistant", "tool_calls": []}


class FakeLLM:
    async def generate_response(self, messages, tools):
        return FakeResponse(
            [
                FakeToolCall("1", "search_wikipedia", "{\"query\": \"quantum\"}"),
                FakeToolCall("2", "finish_research", "{\"summary\": \"done\"}"),
            ]
        )


class FakeSourceClient:
    def __init__(self, document):
        self.document = document

    async def search(self, query):
        return [self.document]


@pytest.mark.asyncio
async def test_research_agent_consumes_normalized_documents():
    agent = ResearchAgent(FakeLLM())
    agent.wiki = FakeSourceClient(Document(source="wikipedia", title="Wiki", content="Wiki content", url="https://example.com/wiki"))
    agent.arxiv = FakeSourceClient(Document(source="arxiv", title="Paper", content="Paper content", url="https://example.com/paper"))
    agent.web = FakeSourceClient(Document(source="web", title="Web", content="Web content", url="https://example.com/web"))

    documents = await agent.run("quantum", max_iterations=1)

    assert [doc.source for doc in documents] == ["wikipedia"]
    assert documents[0].content == "Wiki content"


class FutureToolLLM:
    async def generate_response(self, messages, tools):
        return FakeResponse(
            [
                FakeToolCall("1", "search_pubmed", "{\"query\": \"cancer\"}"),
                FakeToolCall("2", "finish_research", "{\"summary\": \"done\"}"),
            ]
        )


@pytest.mark.asyncio
async def test_research_agent_ignores_future_tools_without_clients():
    agent = ResearchAgent(FutureToolLLM())

    documents = await agent.run("cancer", max_iterations=1)

    assert documents == []
