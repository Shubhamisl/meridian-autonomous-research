from src.meridian.application.pipeline.source_router import SourceRouter


def test_get_tools_for_biomedical_returns_expected_tools():
    router = SourceRouter()

    tools = router.get_tools_for_domain("biomedical")

    assert [tool["function"]["name"] for tool in tools] == [
        "search_pubmed",
        "search_arxiv",
        "search_wikipedia",
        "finish_research",
    ]
    assert tools[-1]["function"]["parameters"]["required"] == ["summary"]


def test_get_tools_for_unknown_domain_falls_back_to_general():
    router = SourceRouter()

    tools = router.get_tools_for_domain("astronomy")

    assert [tool["function"]["name"] for tool in tools] == [
        "search_semantic_scholar",
        "search_wikipedia",
        "search_web",
        "finish_research",
    ]
    assert tools[0]["function"]["parameters"]["required"] == ["query"]
