import json
import logging
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


class FakeQueryProcessor:
    def __init__(self, enriched_query="enriched query"):
        self.enriched_query = enriched_query
        self.calls = []

    def enrich(self, raw_query, domain, source):
        self.calls.append((raw_query, domain, source))
        return self.enriched_query


def _finish_and_tool_call(tool_name: str, query: str = "cancer"):
    return FakeResponse(
        [
            FakeToolCall("1", tool_name, json.dumps({"query": query})),
            FakeToolCall("2", "finish_research", "{\"summary\": \"done\"}"),
        ]
    )


def _search_and_finish_calls(*tool_specs: tuple[str, str]):
    tool_calls = []
    for index, (tool_name, query) in enumerate(tool_specs, start=1):
        tool_calls.append(FakeToolCall(str(index), tool_name, json.dumps({"query": query})))
    tool_calls.append(FakeToolCall(str(len(tool_calls) + 1), "finish_research", "{\"summary\": \"done\"}"))
    return FakeResponse(tool_calls)


@pytest.mark.asyncio
async def test_research_agent_enriches_query_before_dispatching_search():
    tools = [{"type": "function", "function": {"name": "search_arxiv", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("biomedical")
    router = FakeRouter(tools)
    llm = FakeLLM([_finish_and_tool_call("search_arxiv")])
    query_processor = FakeQueryProcessor(enriched_query='"quoted" enriched query')
    client = FakeSourceClient(
        Document(source="arxiv", title="ArXiv Title", content="ArXiv abstract", url="https://example.com")
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        arxiv_client=client,
        query_processor=query_processor,
    )

    await agent.run("cancer", max_iterations=1)

    assert query_processor.calls == [("cancer", "biomedical", "arxiv")]
    assert client.calls == ['"quoted" enriched query']


@pytest.mark.asyncio
async def test_research_agent_system_prompt_mentions_search_operators():
    tools = [{"type": "function", "function": {"name": "finish_research", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM([FakeResponse([])])

    agent = ResearchAgent(llm, domain_classifier=classifier, source_router=router)

    await agent.run("cancer", max_iterations=1)

    system_prompt = llm.calls[0]["messages"][0]["content"]
    assert "after:YYYY-MM-DD" in system_prompt
    assert "intitle:" in system_prompt
    assert "-site:" in system_prompt
    assert "quoted phrases" in system_prompt
    assert "combining operators" in system_prompt


@pytest.mark.asyncio
async def test_research_agent_logs_raw_and_enriched_queries_at_debug(caplog):
    tools = [{"type": "function", "function": {"name": "search_web", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM([_finish_and_tool_call("search_web")])
    query_processor = FakeQueryProcessor(enriched_query="enriched web query")
    client = FakeSourceClient(
        Document(source="web", title="Web Title", content="Web body", url="https://example.com")
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        web_search_client=client,
        query_processor=query_processor,
    )

    caplog.set_level(logging.DEBUG)
    await agent.run("cancer", max_iterations=1)

    assert any("raw query='cancer'" in record.message for record in caplog.records)
    assert any("enriched query='enriched web query'" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_research_agent_normalizes_search_arxiv_to_source_label():
    tools = [{"type": "function", "function": {"name": "search_arxiv", "parameters": {"type": "object"}}}]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM([_finish_and_tool_call("search_arxiv")])
    query_processor = FakeQueryProcessor(enriched_query="normalized query")
    client = FakeSourceClient(
        Document(source="arxiv", title="ArXiv Title", content="ArXiv abstract", url="https://example.com")
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        arxiv_client=client,
        query_processor=query_processor,
    )

    await agent.run("cancer", max_iterations=1)

    assert query_processor.calls == [("cancer", "general", "arxiv")]


@pytest.mark.asyncio
async def test_research_agent_raises_when_max_iterations_exhaust_with_only_wikipedia_evidence():
    tools = [
        {"type": "function", "function": {"name": "search_wikipedia", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "search_web", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "finish_research", "parameters": {"type": "object"}}},
    ]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM([_search_and_finish_calls(("search_wikipedia", "cancer"))])
    wikipedia_client = FakeSourceClient(
        Document(source="wikipedia", title="Cancer", content="Wikipedia summary", url="https://example.com/wiki")
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        wikipedia_client=wikipedia_client,
    )

    with pytest.raises(RuntimeError, match="non-Wikipedia source"):
        await agent.run("cancer", max_iterations=1)


@pytest.mark.asyncio
async def test_research_agent_raises_when_model_stops_after_blocked_wikipedia_only_finish():
    tools = [
        {"type": "function", "function": {"name": "search_wikipedia", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "search_web", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "finish_research", "parameters": {"type": "object"}}},
    ]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM(
        [
            _search_and_finish_calls(("search_wikipedia", "cancer")),
            FakeResponse([]),
        ]
    )
    wikipedia_client = FakeSourceClient(
        Document(source="wikipedia", title="Cancer", content="Wikipedia summary", url="https://example.com/wiki")
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        wikipedia_client=wikipedia_client,
    )

    with pytest.raises(RuntimeError, match="non-Wikipedia source"):
        await agent.run("cancer", max_iterations=2)


@pytest.mark.asyncio
async def test_research_agent_raises_when_model_stops_after_blocked_single_source_finish():
    tools = [
        {"type": "function", "function": {"name": "search_web", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "search_arxiv", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "finish_research", "parameters": {"type": "object"}}},
    ]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM(
        [
            _search_and_finish_calls(("search_web", "semiconductor supply chains")),
            FakeResponse([]),
        ]
    )
    web_client = FakeSourceClient(
        Document(
            source="web",
            title="Supply chain overview",
            content="Analyst coverage of semiconductor supply chains.",
            url="https://example.com/supply-chain",
        )
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        web_search_client=web_client,
    )

    with pytest.raises(RuntimeError, match="could not finish safely"):
        await agent.run("semiconductor supply chains", max_iterations=2)


@pytest.mark.asyncio
async def test_research_agent_recovers_after_blocked_finish_once_additional_evidence_is_gathered():
    tools = [
        {"type": "function", "function": {"name": "search_web", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "search_arxiv", "parameters": {"type": "object"}}},
        {"type": "function", "function": {"name": "finish_research", "parameters": {"type": "object"}}},
    ]
    classifier = FakeClassifier("general")
    router = FakeRouter(tools)
    llm = FakeLLM(
        [
            _search_and_finish_calls(("search_web", "battery recycling")),
            _search_and_finish_calls(("search_arxiv", "battery recycling")),
        ]
    )
    web_client = FakeSourceClient(
        Document(
            source="web",
            title="Battery recycling market",
            content="Industry reporting on recycling capacity.",
            url="https://example.com/recycling-market",
        )
    )
    arxiv_client = FakeSourceClient(
        Document(
            source="arxiv",
            title="Battery recycling methods",
            content="Research paper on recycling methods.",
            url="https://arxiv.org/abs/1234.5678",
        )
    )

    agent = ResearchAgent(
        llm,
        domain_classifier=classifier,
        source_router=router,
        web_search_client=web_client,
        arxiv_client=arxiv_client,
    )

    documents = await agent.run("battery recycling", max_iterations=2)

    assert [document.source for document in documents] == ["web", "arxiv"]
