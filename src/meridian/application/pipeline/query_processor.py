from __future__ import annotations

import re


class QueryProcessor:
    AFTER_FILTER = "after:2022-01-01"
    WEB_EXCLUSIONS = ("-site:reddit.com", "-site:quora.com")
    PHRASE_SOURCES = {"arxiv", "pubmed"}
    BOOLEAN_OPERATORS = {"AND", "OR", "NOT"}

    def enrich(self, raw_query: str, domain: str, source: str) -> str:
        try:
            if not isinstance(raw_query, str):
                return raw_query

            if not raw_query.strip():
                return raw_query

            domain_key = domain.lower() if isinstance(domain, str) else ""
            source_key = source.lower() if isinstance(source, str) else ""

            tokens = self._tokenize(raw_query)
            if not tokens or not self._has_intent_term(tokens):
                return raw_query

            if source_key in self.PHRASE_SOURCES and not self._contains_unsafe_academic_syntax(tokens):
                tokens = self._quote_multi_word_runs(tokens)

            tokens = self._add_domain_filters(tokens, domain_key)
            tokens = self._add_source_filters(tokens, source_key)

            enriched = " ".join(tokens).strip()
            if not enriched:
                return raw_query

            return enriched
        except Exception:
            return raw_query

    def _tokenize(self, raw_query: str) -> list[str]:
        if raw_query.count('"') % 2 != 0:
            return []

        normalized = re.sub(r"\s+", " ", raw_query.strip())
        if not normalized:
            return []

        raw_tokens = re.findall(r'"[^"]*"|\S+', normalized)
        tokens: list[str] = []
        index = 0

        while index < len(raw_tokens):
            token = raw_tokens[index]
            lower = token.lower()

            if lower in {"after:", "-site:"}:
                if index + 1 >= len(raw_tokens):
                    return []
                tokens.append(f"{lower}{raw_tokens[index + 1]}")
                index += 2
                continue

            if token.startswith('"') and token.endswith('"'):
                inner = re.sub(r"\s+", " ", token[1:-1].strip())
                if not inner:
                    return []
                tokens.append(f'"{inner}"')
            else:
                tokens.append(token)

            index += 1

        return tokens

    def _has_intent_term(self, tokens: list[str]) -> bool:
        return any(not self._is_operator(token) for token in tokens)

    def _quote_multi_word_runs(self, tokens: list[str]) -> list[str]:
        quoted_tokens: list[str] = []
        pending_terms: list[str] = []

        def flush_pending_terms() -> None:
            if not pending_terms:
                return
            if len(pending_terms) == 1:
                quoted_tokens.append(pending_terms[0])
            else:
                quoted_tokens.append(f'"{" ".join(pending_terms)}"')
            pending_terms.clear()

        for token in tokens:
            if self._is_operator(token) or self._is_quoted_phrase(token):
                flush_pending_terms()
                quoted_tokens.append(token)
                continue

            pending_terms.append(token)

        flush_pending_terms()
        return quoted_tokens

    def _contains_unsafe_academic_syntax(self, tokens: list[str]) -> bool:
        return any(
            self._is_boolean_operator(token)
            or self._has_fielded_query_syntax(token)
            or self._has_grouping_syntax(token)
            for token in tokens
        )

    def _add_domain_filters(self, tokens: list[str], domain: str) -> list[str]:
        if domain not in {"computer_science", "biomedical"}:
            return tokens

        if any(token.lower().startswith("after:") for token in tokens):
            return tokens

        return [*tokens, self.AFTER_FILTER]

    def _add_source_filters(self, tokens: list[str], source: str) -> list[str]:
        if source != "web":
            return tokens

        existing_sites = {
            self._site_value(token)
            for token in tokens
            if token.lower().startswith("-site:")
        }

        enriched_tokens = list(tokens)
        for exclusion in self.WEB_EXCLUSIONS:
            if self._site_value(exclusion) not in existing_sites:
                enriched_tokens.append(exclusion)

        return enriched_tokens

    def _is_operator(self, token: str) -> bool:
        lowered = token.lower()
        return lowered.startswith("after:") or lowered.startswith("-site:")

    def _is_boolean_operator(self, token: str) -> bool:
        return token in self.BOOLEAN_OPERATORS

    def _has_fielded_query_syntax(self, token: str) -> bool:
        return ":" in token and not self._is_operator(token)

    def _has_grouping_syntax(self, token: str) -> bool:
        return "(" in token or ")" in token

    def _is_quoted_phrase(self, token: str) -> bool:
        return len(token) >= 2 and token.startswith('"') and token.endswith('"')

    def _site_value(self, token: str) -> str:
        return token.split(":", 1)[1].lower() if ":" in token else token.lower()
