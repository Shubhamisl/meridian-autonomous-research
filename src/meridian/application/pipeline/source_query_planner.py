from __future__ import annotations

import re


class SourceQueryPlanner:
    def compile(self, user_query: str, execution_query: str, domain: str, source: str) -> str:
        source_key = source.lower() if isinstance(source, str) else ""
        if source_key == "pubmed":
            return self._compile_pubmed(user_query, execution_query)
        if source_key == "arxiv":
            return self._compile_arxiv(user_query, execution_query)
        return self._sanitize_or_fallback(execution_query, user_query)

    def refine(
        self,
        user_query: str,
        domain: str,
        attempted_queries: list[str],
        rejection_reasons: list[str],
    ) -> str:
        return user_query

    def _compile_pubmed(self, user_query: str, execution_query: str) -> str:
        base_query = self._sanitize_or_fallback(execution_query, user_query)
        return f'({base_query}) AND ("2022"[Date - Publication] : "3000"[Date - Publication])'

    def _compile_arxiv(self, user_query: str, execution_query: str) -> str:
        return self._sanitize_or_fallback(execution_query, user_query)

    def _sanitize_or_fallback(self, query: str, fallback: str) -> str:
        cleaned = self._strip_after_operator(query)
        if cleaned:
            return cleaned
        return self._strip_after_operator(fallback)

    def _strip_after_operator(self, query: str) -> str:
        cleaned = re.sub(r"\s*after:\S+", "", query or "").strip()
        return re.sub(r"\s+", " ", cleaned)
