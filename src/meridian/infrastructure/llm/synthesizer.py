from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient
from src.meridian.infrastructure.llm.report_templates import REPORT_TEMPLATES
from src.meridian.domain.entities import Chunk, ResearchReport

class ReportSynthesizer:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.llm = openrouter_client

    async def synthesize(
        self,
        job_id: str,
        query: str,
        chunks: list[Chunk],
        format_label: str = "general",
        report_depth: str = "standard",
    ) -> ResearchReport:
        context_text = "\n\n".join(
            [f"Source: {c.metadata.get('title', c.metadata.get('source', 'Unknown'))}\n---\n{c.content}" for c in chunks]
        )
        system_prompt = REPORT_TEMPLATES.get(format_label, REPORT_TEMPLATES["general"])
        depth_instruction = (
            "Provide a deeper analysis with more supporting detail, explicit tradeoffs, caveats, "
            "and surfaced uncertainty grounded in the supplied evidence."
            if report_depth == "deep"
            else "Provide a standard-depth report that is complete, readable, and grounded in the supplied evidence."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Topic: {query}\n\nContext Context:\n{context_text}\n\n"
                    "Write a complete markdown report synthesizing the material. "
                    f"{depth_instruction} "
                    "Use markdown headings, bullet points, and inline references (e.g. '[1]', '[Source]', "
                    "or linked titles) pointing back to the context sources."
                ),
            },
        ]

        response = await self.llm.generate_response(messages=messages)
        content = response.content if response.content else "Synthesis failed to return content."

        return ResearchReport(
            job_id=job_id,
            query=query,
            markdown_content=content
        )
