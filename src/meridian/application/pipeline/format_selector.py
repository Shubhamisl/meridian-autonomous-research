from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient


class FormatSelector:
    ALLOWED_LABELS = {"imrad", "mece", "osint", "general"}
    LABEL_ORDER = ("imrad", "osint", "mece", "general")
    DOMAIN_DEFAULTS = {
        "biomedical": "imrad",
        "computer_science": "general",
        "economics": "mece",
        "legal": "general",
        "general": "general",
    }
    SIGNAL_KEYWORDS = {
        "osint": (
            "threat",
            "vulnerability",
            "attack",
            "breach",
            "exploit",
            "actor",
            "campaign",
            "intrusion",
            "malware",
            "ioc",
            "tactic",
        ),
        "mece": (
            "market",
            "strategy",
            "revenue",
            "competitive",
            "analysis",
            "recommend",
            "pricing",
            "adoption",
            "growth",
            "investment",
        ),
        "imrad": (
            "trial",
            "systematic review",
            "meta-analysis",
            "efficacy",
            "cohort",
            "clinical",
            "outcomes",
            "biomarker",
        ),
    }

    def __init__(self, openrouter_client: OpenRouterClient):
        self.llm = openrouter_client

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().replace("-", " ").replace("_", " ").split())

    def _normalize_label(self, raw_label: str) -> str:
        label = raw_label.strip().lower()
        if ":" in label:
            prefix, suffix = label.split(":", 1)
            if prefix.strip() in {"label", "format", "structure", "recommendation"}:
                label = suffix.strip()

        label = label.strip("\"'`.,:;!?")
        return "_".join(label.replace("-", " ").split())

    def _match_counts(self, query: str) -> dict[str, int]:
        normalized_query = self._normalize_text(query)
        counts: dict[str, int] = {}

        for label, keywords in self.SIGNAL_KEYWORDS.items():
            counts[label] = sum(
                1 for keyword in keywords if self._normalize_text(keyword) in normalized_query
            )

        return counts

    def _rule_based_recommendation(self, domain: str, query: str) -> tuple[str, list[str]]:
        default_label = self.DOMAIN_DEFAULTS.get(domain, "general")
        counts = self._match_counts(query)
        matched_labels = [label for label, count in counts.items() if count > 0]

        if not matched_labels:
            return default_label, []

        if len(matched_labels) == 1:
            return matched_labels[0], []

        ranked_matches = [label for label in self.LABEL_ORDER if label in matched_labels]
        rule_based_recommendation = ranked_matches[0]
        competing_candidates = ranked_matches[1:]
        return rule_based_recommendation, competing_candidates

    def _build_messages(
        self,
        domain: str,
        query: str,
        rule_based_recommendation: str,
        competing_candidates: list[str],
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are selecting the best report format for a research synthesis system. "
                    "Return exactly one label and nothing else: imrad, mece, osint, general."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Domain: {domain}\n"
                    f"Query: {query}\n"
                    f"Rule-based recommendation: {rule_based_recommendation}\n"
                    f"Competing candidates: {', '.join(competing_candidates) if competing_candidates else 'none'}"
                ),
            },
        ]

    async def _llm_tiebreaker(
        self,
        domain: str,
        query: str,
        rule_based_recommendation: str,
        competing_candidates: list[str],
    ) -> str | None:
        try:
            response = await self.llm.generate_response(
                messages=self._build_messages(domain, query, rule_based_recommendation, competing_candidates)
            )
        except Exception:
            return None

        label = self._normalize_label(getattr(response, "content", "") or "")
        if label in self.ALLOWED_LABELS:
            return label
        return None

    async def select(self, domain: str, query: str) -> str:
        rule_based_recommendation, competing_candidates = self._rule_based_recommendation(domain, query)

        if not competing_candidates:
            return rule_based_recommendation

        llm_label = await self._llm_tiebreaker(domain, query, rule_based_recommendation, competing_candidates)
        if llm_label is not None:
            return llm_label

        return rule_based_recommendation
