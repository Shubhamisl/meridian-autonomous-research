import pytest

from src.meridian.application.pipeline.format_selector import FormatSelector


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeOpenRouterClient:
    def __init__(self, response_text: str | None = None, error: Exception | None = None):
        self.response_text = response_text
        self.error = error
        self.calls = 0
        self.last_messages = None

    async def generate_response(self, messages):
        self.calls += 1
        self.last_messages = messages
        if self.error is not None:
            raise self.error
        return FakeResponse(self.response_text or "")


@pytest.mark.asyncio
async def test_biomedical_defaults_to_imrad_without_calling_llm():
    client = FakeOpenRouterClient("osint")
    selector = FormatSelector(client)

    result = await selector.select(
        "biomedical",
        "Summarize the findings from a randomized clinical trial.",
    )

    assert result == "imrad"
    assert client.calls == 0


@pytest.mark.asyncio
async def test_strong_security_query_promotes_osint():
    client = FakeOpenRouterClient("general")
    selector = FormatSelector(client)

    result = await selector.select(
        "computer_science",
        "Analyze the vulnerability disclosure, threat actors, and intrusion campaign indicators.",
    )

    assert result == "osint"
    assert client.calls == 0


@pytest.mark.asyncio
async def test_mixed_mece_and_osint_signals_trigger_llm_tiebreaker():
    client = FakeOpenRouterClient("mece")
    selector = FormatSelector(client)

    result = await selector.select(
        "general",
        "Analyze the breach campaign, market strategy, and revenue impact.",
    )

    assert result == "mece"
    assert client.calls == 1
    assert client.last_messages is not None
    assert "general" in client.last_messages[0]["content"].lower()
    assert "breach campaign" in client.last_messages[1]["content"].lower()
    assert "rule-based recommendation" in client.last_messages[1]["content"].lower()
    assert "competing candidates: mece, osint" in client.last_messages[1]["content"].lower()


@pytest.mark.asyncio
async def test_invalid_llm_label_falls_back_to_rule_result():
    client = FakeOpenRouterClient("definitely-not-a-format")
    selector = FormatSelector(client)

    result = await selector.select(
        "general",
        "Analyze the breach campaign, market strategy, and revenue impact.",
    )

    assert result == "general"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_llm_exception_falls_back_to_rule_result():
    client = FakeOpenRouterClient(error=RuntimeError("boom"))
    selector = FormatSelector(client)

    result = await selector.select(
        "general",
        "Analyze the breach campaign, market strategy, and revenue impact.",
    )

    assert result == "general"
    assert client.calls == 1
