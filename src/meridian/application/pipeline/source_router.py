class SourceRouter:
    def __init__(self):
        self._tool_sets = {
            "biomedical": [
                self._tool("search_pubmed", "Search PubMed for biomedical literature"),
                self._tool("search_arxiv", "Search ArXiv for academic papers on a topic"),
                self._tool("search_wikipedia", "Search Wikipedia for a given query"),
                self._tool("finish_research", "Call this when you have gathered enough information to answer the user's research query.", parameter_name="summary"),
            ],
            "computer_science": [
                self._tool("search_arxiv", "Search ArXiv for academic papers on a topic"),
                self._tool("search_ieee", "Search IEEE for computer science and engineering literature"),
                self._tool("search_web", "Search the web for recent news or general information"),
                self._tool("finish_research", "Call this when you have gathered enough information to answer the user's research query.", parameter_name="summary"),
            ],
            "economics": [
                self._tool("search_semantic_scholar", "Search Semantic Scholar for economics and academic literature"),
                self._tool("search_web", "Search the web for recent news or general information"),
                self._tool("search_wikipedia", "Search Wikipedia for a given query"),
                self._tool("finish_research", "Call this when you have gathered enough information to answer the user's research query.", parameter_name="summary"),
            ],
            "legal": [
                self._tool("search_web", "Search the web for recent news or general information"),
                self._tool("search_wikipedia", "Search Wikipedia for a given query"),
                self._tool("finish_research", "Call this when you have gathered enough information to answer the user's research query.", parameter_name="summary"),
            ],
            "general": [
                self._tool("search_semantic_scholar", "Search Semantic Scholar for academic literature"),
                self._tool("search_wikipedia", "Search Wikipedia for a given query"),
                self._tool("search_web", "Search the web for recent news or general information"),
                self._tool("finish_research", "Call this when you have gathered enough information to answer the user's research query.", parameter_name="summary"),
            ],
        }

    def _tool(self, name: str, description: str, parameter_name: str = "query") -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {parameter_name: {"type": "string"}},
                    "required": [parameter_name],
                },
            },
        }

    def get_tools_for_domain(self, domain: str) -> list[dict]:
        return self._tool_sets.get(domain, self._tool_sets["general"])
