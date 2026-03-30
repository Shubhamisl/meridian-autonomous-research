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


def test_pubmed_boolean_query_preserves_or_semantics():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="gene therapy OR crispr",
        execution_query="gene therapy OR crispr after:2022-01-01",
        domain="biomedical",
        source="pubmed",
    )

    assert "after:" not in compiled
    assert compiled.startswith("(gene therapy OR crispr)")
    assert compiled.endswith('AND ("2022"[Date - Publication] : "3000"[Date - Publication])')


def test_pubmed_uses_user_query_when_execution_query_is_blank():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="gene therapy OR crispr",
        execution_query="",
        domain="biomedical",
        source="pubmed",
    )

    assert "after:" not in compiled
    assert "gene therapy OR crispr" in compiled
    assert "2022" in compiled


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


def test_non_academic_source_sanitizes_unsupported_operator_leakage():
    planner = SourceQueryPlanner()

    compiled = planner.compile(
        user_query="recent advances",
        execution_query="recent advances after:2022-01-01",
        domain="general",
        source="semantic_scholar",
    )

    assert compiled == "recent advances"
