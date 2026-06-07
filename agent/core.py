"""
core.py — Main ShopRadar agent loop.

The flow:
  1. User gives a research query in natural language
  2. Planner breaks it into sub-tasks (which platforms, what fields, what question)
  3. For each platform: Codex generates a scraper → run it → collect data
  4. Analyzer generates analysis code → run it → get insights
  5. Reporter turns insights into a Markdown + CSV report

Steps 3 and 4 require Codex API access. Steps 1, 2, 5 work with gpt-3.5-turbo.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

from agent.planner  import Planner, ResearchPlan
from agent.reporter import Reporter
from codex import scraper_gen, analyzer_gen
from platforms import naver, coupang

load_dotenv()
logger = logging.getLogger(__name__)


class ShopRadarAgent:
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        self.planner    = Planner()
        self.reporter   = Reporter()
        os.makedirs(output_dir, exist_ok=True)

    def research(self, query: str) -> Optional[dict]:
        """
        Run a full market research loop for the given query.

        Args:
            query: Natural language research question
                   e.g. "쿠팡에서 무선 이어폰 3만원 이하 경쟁 분석"

        Returns:
            Dict with keys: summary, findings, report_path, csv_path
        """
        logger.info(f"Starting research: {query!r}")

        # Step 1 — Plan
        plan: ResearchPlan = self.planner.plan(query)
        logger.info(f"Plan: platforms={plan.platforms}, keyword={plan.keyword!r}")

        # Step 2 — Collect data from each platform
        all_products: list[dict] = []

        for platform in plan.platforms:
            logger.info(f"Collecting from: {platform}")
            products = self._collect(platform, plan)
            if products:
                all_products.extend(products)
                logger.info(f"  → {len(products)} products collected")
            else:
                logger.warning(f"  → No data from {platform}")

        if not all_products:
            logger.error("No data collected from any platform.")
            return None

        df = pd.DataFrame(all_products)
        logger.info(f"Total: {len(df)} products across {df['platform'].nunique()} platform(s)")

        # Step 3 — Analyze
        # Try Codex-generated analysis first; fall back to simple pandas analysis
        findings = analyzer_gen.generate_analysis(df, plan.research_question)
        if not findings:
            logger.warning("Codex analysis failed; using simple analysis fallback")
            findings = analyzer_gen.simple_analysis(df)

        # Step 4 — Report
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M")
        base_name  = f"{plan.keyword.replace(' ', '_')}_{timestamp}"
        report_path = os.path.join(self.output_dir, base_name + ".md")
        csv_path    = os.path.join(self.output_dir, base_name + ".csv")

        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        self.reporter.write(
            path=report_path,
            query=query,
            plan=plan,
            df=df,
            findings=findings,
        )

        logger.info(f"Report saved: {report_path}")
        logger.info(f"CSV saved:    {csv_path}")

        return {
            "summary":     findings.get("key_findings", []),
            "findings":    findings,
            "report_path": report_path,
            "csv_path":    csv_path,
            "n_products":  len(df),
        }

    def _collect(self, platform: str, plan: "ResearchPlan") -> list[dict]:
        """Collect products from a single platform and normalise to dicts."""
        try:
            if platform == "naver":
                raw = naver.search(plan.keyword, sort=plan.sort, max_pages=plan.max_pages)
                return [
                    {
                        "platform":     "naver",
                        "title":        p.title,
                        "price":        p.price,
                        "review_count": p.review_count,
                        "rating":       p.rating,
                        "seller":       p.seller,
                        "is_ad":        p.is_ad,
                        "link":         p.link,
                    }
                    for p in raw
                ]

            elif platform == "coupang":
                raw = coupang.search(plan.keyword, max_pages=plan.max_pages)
                return [
                    {
                        "platform":     "coupang",
                        "title":        p.title,
                        "price":        p.price,
                        "review_count": p.review_count,
                        "rating":       p.rating,
                        "seller":       None,          # Coupang doesn't expose seller name easily
                        "is_ad":        False,
                        "link":         p.link,
                    }
                    for p in raw
                ]

            else:
                # For platforms not yet implemented (11번가, G마켓),
                # try asking Codex to generate a scraper on the fly
                logger.info(f"Trying Codex-generated scraper for: {platform}")
                code = scraper_gen.generate_scraper(
                    platform=platform,
                    keyword=plan.keyword,
                    fields=["title", "price", "review_count", "seller", "link"],
                    sort=plan.sort,
                    max_results=plan.max_pages * 40,
                )
                if not code:
                    return []

                import json
                output = scraper_gen.run_generated_code(code)
                if not output:
                    return []

                products = json.loads(output)
                for p in products:
                    p["platform"] = platform
                return products

        except Exception as e:
            logger.error(f"Collection failed for {platform}: {e}")
            return []
