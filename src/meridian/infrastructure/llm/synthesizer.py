from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient
from src.meridian.domain.entities import Chunk, ResearchReport

class ReportSynthesizer:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.llm = openrouter_client
        
    async def synthesize(self, job_id: str, query: str, chunks: list[Chunk]) -> ResearchReport:
        context_text = "\n\n".join([f"Source: {c.metadata.get('title', c.metadata.get('source', 'Unknown'))}\n---\n{c.content}" for c in chunks])
        
        messages = [
            {"role": "system", "content": "You are an expert research analyst. Your task is to write a highly detailed, comprehensive, and well-structured markdown report based heavily on the provided context. Context snippets are provided below."},
            {"role": "user", "content": f"Topic: {query}\n\nContext Context:\n{context_text}\n\nWrite a complete markdown report synthesizing the material. Use markdown headings, bullet points, and inline references (e.g. '[1]', '[Source]', or linked titles) pointing back to the context sources."}
        ]
        
        response = await self.llm.generate_response(messages=messages)
        content = response.content if response.content else "Synthesis failed to return content."
        
        return ResearchReport(
            job_id=job_id,
            query=query,
            markdown_content=content
        )
