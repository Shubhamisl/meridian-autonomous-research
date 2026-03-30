import logging
import json
from typing import List

from src.meridian.application.pipeline.query_processor import QueryProcessor
from src.meridian.application.pipeline.domain_classifier import DomainClassifier
from src.meridian.application.pipeline.source_router import SourceRouter
from src.meridian.domain.entities import Document
from src.meridian.infrastructure.external_apis.arxiv_client import ArXivClient
from src.meridian.infrastructure.external_apis.ieee_client import IEEEClient
from src.meridian.infrastructure.external_apis.pubmed_client import PubMedClient
from src.meridian.infrastructure.external_apis.semantic_scholar_client import SemanticScholarClient
from src.meridian.infrastructure.external_apis.web_search_client import WebSearchClient
from src.meridian.infrastructure.external_apis.wikipedia_client import WikipediaClient
from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient


logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        domain_classifier: DomainClassifier | None = None,
        source_router: SourceRouter | None = None,
        wikipedia_client: WikipediaClient | None = None,
        arxiv_client: ArXivClient | None = None,
        web_search_client: WebSearchClient | None = None,
        pubmed_client: PubMedClient | None = None,
        ieee_client: IEEEClient | None = None,
        semantic_scholar_client: SemanticScholarClient | None = None,
        query_processor: QueryProcessor | None = None,
    ):
        self.llm = openrouter_client
        self.domain_classifier = domain_classifier or DomainClassifier(openrouter_client)
        self.source_router = source_router or SourceRouter()
        self.wikipedia_client = wikipedia_client or WikipediaClient()
        self.arxiv_client = arxiv_client or ArXivClient()
        self.web_search_client = web_search_client or WebSearchClient()
        self.pubmed_client = pubmed_client or PubMedClient()
        self.ieee_client = ieee_client or IEEEClient()
        self.semantic_scholar_client = semantic_scholar_client or SemanticScholarClient()
        self.query_processor = query_processor or QueryProcessor()
        self.domain = "general"
        self.active_sources: list[str] = []
        self.query_refinements: list[dict[str, str]] = []

    async def run(self, topic: str, max_iterations: int = 5) -> List[Document]:
        self.domain = await self.domain_classifier.classify(topic)
        tools = self.source_router.get_tools_for_domain(self.domain)
        self.active_sources = []
        self.query_refinements = []

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an autonomous research intelligence agent. Your job is to "
                    "iteratively search the available sources to gather sufficient "
                    "information to write a comprehensive report on the user's query. "
                    "Whenever possible, gather evidence from at least two complementary "
                    "sources before you call finish_research, and do not rely on only "
                    "Wikipedia when other sources are available. "
                    "When you have enough context, call finish_research. "
                    "Use search operators such as after:YYYY-MM-DD, intitle:, -site:, "
                    "quoted phrases, and combining operators when they improve recall."
                ),
            },
            {"role": "user", "content": f"Please research the following topic: {topic}"},
        ]

        documents: list[Document] = []
        finish_research_blocked = False
        available_search_tools = [
            tool["function"]["name"]
            for tool in tools
            if tool["function"]["name"] != "finish_research"
        ]

        def _document_payload(result: Document) -> dict:
            if hasattr(result, "model_dump"):
                return result.model_dump(mode="json")
            return result.dict()

        def _result_fields(result):
            if isinstance(result, Document):
                return result.source, result.url, result.title, result.content

            return (
                getattr(result, "source", ""),
                getattr(result, "url", ""),
                getattr(result, "title", ""),
                getattr(result, "content", getattr(result, "summary", getattr(result, "body", ""))),
            )

        def _source_label(tool_name: str) -> str:
            mapping = {
                "search_web": "web",
                "search_arxiv": "arxiv",
                "search_pubmed": "pubmed",
                "search_ieee": "ieee",
                "search_semantic_scholar": "semantic_scholar",
                "search_wikipedia": "wikipedia",
            }
            return mapping.get(tool_name, tool_name.removeprefix("search_"))

        async def _run_search(client, query: str):
            if client is None:
                return []
            return await client.search(query)

        async def _dispatch_search(source: str, query: str):
            match source:
                case "wikipedia":
                    return await _run_search(self.wikipedia_client, query)
                case "arxiv":
                    return await _run_search(self.arxiv_client, query)
                case "web":
                    return await _run_search(self.web_search_client, query)
                case "pubmed":
                    return await _run_search(self.pubmed_client, query)
                case "ieee":
                    return await _run_search(self.ieee_client, query)
                case "semantic_scholar":
                    return await _run_search(self.semantic_scholar_client, query)
                case _:
                    return []

        def _can_finish_research() -> bool:
            unique_sources = {document.source for document in documents if document.source}
            if len(available_search_tools) < 2:
                return True
            if len(unique_sources) < 2:
                return False
            return unique_sources != {"wikipedia"}

        def _has_wikipedia_only_evidence() -> bool:
            if len(available_search_tools) < 2:
                return False
            unique_sources = {document.source for document in documents if document.source}
            return unique_sources == {"wikipedia"}

        def _raise_incomplete_research_error() -> None:
            if _has_wikipedia_only_evidence():
                raise RuntimeError(
                    "Research could not finish safely: gather at least one additional non-Wikipedia source "
                    "before completing."
                )

            raise RuntimeError(
                "Research could not finish safely: finish_research was blocked because the evidence "
                "is still insufficient. Gather additional complementary sources before completing."
            )

        for _ in range(max_iterations):
            response = await self.llm.generate_response(messages=messages, tools=tools)
            response_message = response.model_dump(exclude_unset=True)
            messages.append(response_message)

            if not response.tool_calls:
                break

            all_finished = False
            for tool_call in response.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {"query": topic}

                tool_result_content = ""

                if func_name == "finish_research":
                    if _can_finish_research():
                        all_finished = True
                        finish_research_blocked = False
                        tool_result_content = "Research successfully concluded. Proceed to generation."
                    else:
                        finish_research_blocked = True
                        tool_result_content = (
                            "Research is not complete yet. Gather at least one additional "
                            "non-Wikipedia source before finishing."
                        )
                else:
                    raw_query = args.get("query", topic)
                    source = _source_label(func_name)
                    enriched_query = self.query_processor.enrich(raw_query, self.domain, source)
                    logger.debug(
                        "Dispatching search for %s with raw query=%r enriched query=%r",
                        source,
                        raw_query,
                        enriched_query,
                    )
                    results = await _dispatch_search(source, enriched_query)
                    tool_result_content = json.dumps([_document_payload(r) for r in results])
                    if results:
                        if source not in self.active_sources:
                            self.active_sources.append(source)
                        refinement = {
                            "source": source,
                            "raw_query": raw_query,
                            "enriched_query": enriched_query,
                        }
                        if refinement not in self.query_refinements:
                            self.query_refinements.append(refinement)
                    for r in results:
                        source, url, title, content = _result_fields(r)
                        documents.append(Document(source=source or self.domain, url=url, title=title, content=content))

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": tool_result_content,
                    }
                )

            if all_finished:
                break

        if finish_research_blocked:
            _raise_incomplete_research_error()

        if _has_wikipedia_only_evidence():
            _raise_incomplete_research_error()

        return documents
