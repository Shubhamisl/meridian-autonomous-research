import json
from typing import List, Dict, Any
from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient
from src.meridian.infrastructure.external_apis.wikipedia_client import WikipediaClient
from src.meridian.infrastructure.external_apis.arxiv_client import ArXivClient
from src.meridian.infrastructure.external_apis.web_search_client import WebSearchClient
from src.meridian.domain.entities import Document

class ResearchAgent:
    def __init__(self, openrouter_client: OpenRouterClient):
        self.llm = openrouter_client
        self.wiki = WikipediaClient()
        self.arxiv = ArXivClient()
        self.web = WebSearchClient()
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_wikipedia",
                    "description": "Search Wikipedia for a given query",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_arxiv",
                    "description": "Search ArXiv for academic papers on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for recent news or general information",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finish_research",
                    "description": "Call this when you have gathered enough information to answer the user's research query.",
                    "parameters": {
                        "type": "object",
                        "properties": {"summary": {"type": "string"}},
                        "required": ["summary"]
                    }
                }
            }
        ]

    async def run(self, topic: str, max_iterations: int = 5) -> List[Document]:
        messages = [
            {"role": "system", "content": "You are an autonomous research intelligence agent. Your job is to iteratively search Wikipedia, ArXiv, and the Web to gather sufficient information to write a comprehensive report on the user's query. When you have enough context, call finish_research."},
            {"role": "user", "content": f"Please research the following topic: {topic}"}
        ]
        
        documents = []
        
        for _ in range(max_iterations):
            response = await self.llm.generate_response(messages=messages, tools=self.tools)
            
            # Using model_dump to cleanly append the response message
            response_message = response.model_dump(exclude_unset=True)
            messages.append(response_message)
            
            if not response.tool_calls:
                break
                
            all_finished = False
            for tool_call in response.tool_calls:
                func_name = tool_call.function.name
                # Handle possible invalid json arguments from LLMS gracefully
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {"query": topic}
                    
                tool_result_content = ""
                
                if func_name == "search_wikipedia":
                    results = await self.wiki.search(args.get("query", topic))
                    tool_result_content = json.dumps([r.dict() for r in results])
                    for r in results:
                        documents.append(Document(source="wikipedia", url=r.url, title=r.title, content=r.summary))
                elif func_name == "search_arxiv":
                    results = await self.arxiv.search(args.get("query", topic))
                    tool_result_content = json.dumps([r.dict() for r in results])
                    for r in results:
                        documents.append(Document(source="arxiv", url=r.url, title=r.title, content=r.summary))
                elif func_name == "search_web":
                    results = await self.web.search(args.get("query", topic))
                    tool_result_content = json.dumps([r.dict() for r in results])
                    for r in results:
                        documents.append(Document(source="web", url=r.url, title=r.title, content=r.body))
                elif func_name == "finish_research":
                    all_finished = True
                    tool_result_content = "Research successfully concluded. Proceed to generation."
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": tool_result_content
                })
                
            if all_finished:
                break
                
        return documents
