from src.meridian.application.pipeline.source_query_planner import SourceQueryPlanner


def test_pubmed_query_does_not_leak_after_operator():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="Recent advances in mRNA vaccines",
        execution_query='"mRNA vaccine" after:2022-01-01',
        domain="biomedical",
        source="pubmed",
    )

    assert "after:" not in compiled
    assert "2022" in compiled
    assert '"mRNA vaccine"' in compiled


def test_arxiv_query_prefers_clean_phrase_search():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="Recent advances in mRNA vaccines",
        execution_query='"mRNA vaccine" after:2022-01-01',
        domain="biomedical",
        source="arxiv",
    )

    assert "after:" not in compiled
    assert '"mRNA vaccine"' in compiled
