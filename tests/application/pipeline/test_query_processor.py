import pytest

from src.meridian.application.pipeline.query_processor import QueryProcessor


@pytest.fixture()
def processor() -> QueryProcessor:
    return QueryProcessor()


def test_enrich_adds_after_date_for_computer_science_when_missing(processor: QueryProcessor) -> None:
    result = processor.enrich("vector databases", "computer_science", "wikipedia")

    assert result == "vector databases after:2022-01-01"


def test_enrich_preserves_existing_after_filter(processor: QueryProcessor) -> None:
    result = processor.enrich("vector databases after:2020-01-01", "computer_science", "wikipedia")

    assert result == "vector databases after:2020-01-01"


def test_enrich_adds_web_exclusions_when_missing(processor: QueryProcessor) -> None:
    result = processor.enrich("open source search", "web", "web")

    assert result == "open source search -site:reddit.com -site:quora.com"


def test_enrich_preserves_existing_web_exclusion(processor: QueryProcessor) -> None:
    result = processor.enrich("open source search -site:reddit.com", "web", "web")

    assert result == "open source search -site:reddit.com -site:quora.com"


def test_enrich_quotes_multi_word_phrase_for_pubmed(processor: QueryProcessor) -> None:
    result = processor.enrich("machine learning", "biomedical", "pubmed")

    assert result == '"machine learning" after:2022-01-01'


def test_enrich_preserves_already_quoted_phrase(processor: QueryProcessor) -> None:
    result = processor.enrich('"machine learning" cancer', "biomedical", "pubmed")

    assert result == '"machine learning" cancer after:2022-01-01'


def test_enrich_preserves_core_terms_under_aggressive_rewrite(processor: QueryProcessor) -> None:
    result = processor.enrich("   deep   learning   transformers   ", "computer_science", "arxiv")

    assert result == '"deep learning transformers" after:2022-01-01'


@pytest.mark.parametrize("raw_query", ["", "   "])
def test_enrich_returns_raw_input_safely_for_broken_input(processor: QueryProcessor, raw_query: str) -> None:
    assert processor.enrich(raw_query, "computer_science", "arxiv") == raw_query
