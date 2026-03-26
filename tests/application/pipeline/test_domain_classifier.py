import pytest

from src.meridian.application.pipeline.domain_classifier import DomainClassifier


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeOpenRouterClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_messages = None

    async def generate_response(self, messages):
        self.last_messages = messages
        return FakeResponse(self.response_text)


@pytest.mark.asyncio
async def test_classify_normalizes_valid_label():
    client = FakeOpenRouterClient("  Computer_Science \n")
    classifier = DomainClassifier(client)

    result = await classifier.classify("How do transformers work?")

    assert result == "computer_science"
    assert client.last_messages[0]["role"] == "system"
    assert "exactly one label" in client.last_messages[0]["content"].lower()


@pytest.mark.asyncio
async def test_classify_falls_back_to_general_for_invalid_output():
    client = FakeOpenRouterClient("unknown-domain")
    classifier = DomainClassifier(client)

    result = await classifier.classify("What is the best cuisine?")

    assert result == "general"
