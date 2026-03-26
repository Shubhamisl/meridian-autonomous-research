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


class FakeClassifier:
    def __init__(self, domain):
        self.domain = domain
        self.calls = []

    async def classify(self, topic):
        self.calls.append(topic)
        return self.domain


class FakeRouter:
    def __init__(self, tools):
        self.tools = tools
        self.calls = []

    def get_tools_for_domain(self, domain):
        self.calls.append(domain)
        return self.tools


class FakeLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def generate_response(self, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        return self.responses.pop(0)


class FakeSourceClient:
    def __init__(self, document):
        self.document = document
        self.calls = []

    async def search(self, query):
        self.calls.append(query)
        return [self.document]


def _finish_and_tool_call(tool_name: str):
    return FakeResponse(
        [
            FakeToolCall("1", tool_name, "{\"query\": \"cancer\"}"),
            FakeToolCall("2", "finish_research", "{\"summary\": \"done\"}"),
        ]
    )


@pytest.mark.asyncio
async def test_research_agent_stores_classified_domain_and_uses_router_tools():
    tools = [{"type": "function", "function": {"name": "search_pubmed", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("biomedical")
    router = FakeRouter(tools)
    llm = FakeLLM([_finish_and_tool_call("search_pubmed")])
    agent = ResearchAgent(llm, domain_classifier=classifier, source_router=router)
    agent.pubmed_client = FakeSourceClient(Document(source="pubmed", title="PubMed", content="PubMed content", url="https://pubmed.ncbi.nlm.nih.gov/12345/"))

    await agent.run("cancer", max_iterations=1)

    assert agent.domain == "biomedical"
    assert classifier.calls == ["cancer"]
    assert router.calls == ["biomedical"]
    assert llm.calls[0]["tools"] == tools


@pytest.mark.asyncio
async def test_research_agent_dispatches_pubmed_to_injected_client():
    tools = [{"type": "function", "function": {"name": "search_pubmed", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("biomedical")
    router = FakeRouter(tools)
    llm = FakeLLM([_finish_and_tool_call("search_pubmed")])
    agent = ResearchAgent(llm, domain_classifier=classifier, source_router=router)
    pubmed_client = FakeSourceClient(
        Document(
            source="pubmed",
            title="PubMed Title",
            content="PubMed abstract",
            url="https://pubmed.ncbi.nlm.nih.gov/12345/",
        )
    )
    agent.pubmed_client = pubmed_client

    documents = await agent.run("cancer", max_iterations=1)

    assert pubmed_client.calls == ["cancer"]
    assert len(documents) == 1
    assert documents[0].source == "pubmed"
    assert documents[0].title == "PubMed Title"
    assert documents[0].content == "PubMed abstract"
