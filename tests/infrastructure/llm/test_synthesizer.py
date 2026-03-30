import pytest

from src.meridian.domain.entities import Chunk
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer


IMRAD_PROMPT = (
    "You are an expert scientific research analyst. Write a markdown report with sections: "
    "Abstract, Introduction, Methods, Results, Discussion, Limitations, Conclusion. Use cautious "
    "scientific language such as 'the evidence suggests' and 'findings indicate'."
)

MECE_PROMPT = (
    "You are an expert strategy analyst. Write a markdown report that starts with an Executive "
    "Summary using BLUF, uses action-title headings, keeps categories mutually exclusive, and ends "
    "with prioritized Recommendations."
)

OSINT_PROMPT = (
    "You are an expert OSINT analyst. Write a markdown report with sections: Executive Summary "
    "(BLUF, threat level), Scope and Collection Methodology, Findings by theme, Analysis and "
    "Implications, Timeline of key events, Recommendations."
)

GENERAL_PROMPT = (
    "You are an expert research analyst. Your task is to write a highly detailed, comprehensive, "
    "and well-structured markdown report based heavily on the provided context. Context snippets "
    "are provided below."
)


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeOpenRouterClient:
    def __init__(self, response_text: str = "report"):
        self.response_text = response_text
        self.calls = 0
        self.last_messages = None

    async def generate_response(self, messages):
        self.calls += 1
        self.last_messages = messages
        return FakeResponse(self.response_text)


def build_synthesizer():
    return ReportSynthesizer(FakeOpenRouterClient())


def build_chunks():
    return [
        Chunk(
            document_id="doc-1",
            content="Evidence from the source.",
            metadata={"title": "Source A"},
        )
    ]


@pytest.mark.asyncio
async def test_synthesize_uses_osint_template():
    synthesizer = build_synthesizer()

    await synthesizer.synthesize("job-1", "topic", build_chunks(), format_label="osint")

    assert synthesizer.llm.last_messages[0]["content"] == OSINT_PROMPT


@pytest.mark.asyncio
async def test_synthesize_falls_back_to_general_template_for_unknown_label():
    synthesizer = build_synthesizer()

    await synthesizer.synthesize("job-1", "topic", build_chunks(), format_label="not-a-format")

    assert synthesizer.llm.last_messages[0]["content"] == GENERAL_PROMPT


@pytest.mark.asyncio
async def test_synthesize_uses_imrad_template():
    synthesizer = build_synthesizer()

    await synthesizer.synthesize("job-1", "topic", build_chunks(), format_label="imrad")

    assert synthesizer.llm.last_messages[0]["content"] == IMRAD_PROMPT


@pytest.mark.asyncio
async def test_synthesize_uses_mece_template():
    synthesizer = build_synthesizer()

    await synthesizer.synthesize("job-1", "topic", build_chunks(), format_label="mece")

    assert synthesizer.llm.last_messages[0]["content"] == MECE_PROMPT


@pytest.mark.asyncio
async def test_synthesize_adds_deep_report_depth_instruction():
    synthesizer = build_synthesizer()

    await synthesizer.synthesize(
        "job-1",
        "topic",
        build_chunks(),
        format_label="general",
        report_depth="deep",
    )

    assert "deeper analysis" in synthesizer.llm.last_messages[1]["content"]
    assert "supporting detail" in synthesizer.llm.last_messages[1]["content"]
