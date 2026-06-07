"""
planner.py — Parse a natural-language research query into a structured plan.

Uses GPT (not Codex) since this is reasoning, not code generation.
gpt-3.5-turbo handles this well enough and it's cheaper.
"""

import os
import json
import textwrap
import logging
from dataclasses import dataclass, field

import openai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ["naver", "coupang", "eleventh", "gmarket"]

PLAN_PROMPT = textwrap.dedent("""
You are a market research assistant helping a student analyze the Korean e-commerce market.

Parse the following research query and return a JSON object with these fields:
- keyword (string): the main product/category to search for, in Korean if applicable
- platforms (list): which platforms to search — choose from: naver, coupang, eleventh, gmarket
- sort (string): how to sort results — "review" | "price_asc" | "price_desc" | "rank"
- max_pages (int): how many pages to fetch per platform (1-5, default 2)
- price_max (int or null): maximum price filter in KRW if mentioned
- price_min (int or null): minimum price filter in KRW if mentioned
- research_question (string): a clear one-sentence question this research should answer

Return only valid JSON, no explanation.

Query: {query}
""").strip()


@dataclass
class ResearchPlan:
    keyword:           str
    platforms:         list[str]
    sort:              str  = "review"
    max_pages:         int  = 2
    price_max:         int  = None
    price_min:         int  = None
    research_question: str  = ""


class Planner:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")

    def plan(self, query: str) -> ResearchPlan:
        """Convert a free-text query into a structured ResearchPlan."""
        prompt = PLAN_PROMPT.format(query=query)
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise JSON-generating assistant."},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=300,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            return self._validate(data)

        except Exception as e:
            logger.error(f"Planner failed: {e}. Using default plan.")
            # Fall back to a simple keyword extraction
            return ResearchPlan(
                keyword=query[:50],
                platforms=["naver", "coupang"],
                research_question=f"What are the competitive dynamics for: {query}",
            )

    def _validate(self, data: dict) -> ResearchPlan:
        """Sanitize planner output."""
        platforms = [p for p in data.get("platforms", ["naver"]) if p in SUPPORTED_PLATFORMS]
        if not platforms:
            platforms = ["naver"]

        return ResearchPlan(
            keyword=data.get("keyword", "")[:100],
            platforms=platforms,
            sort=data.get("sort", "review"),
            max_pages=min(max(int(data.get("max_pages", 2)), 1), 5),
            price_max=data.get("price_max"),
            price_min=data.get("price_min"),
            research_question=data.get("research_question", ""),
        )
