"""
reporter.py — Turn analysis findings into a readable Markdown report.

No AI needed here - just formatting. Works fine offline.
"""

import os
from datetime import datetime
from typing import Optional

import pandas as pd


class Reporter:
    def write(
        self,
        path: str,
        query: str,
        plan,
        df: pd.DataFrame,
        findings: dict,
    ) -> None:
        lines = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines += [
            f"# Market Research Report",
            f"",
            f"**Query:** {query}",
            f"**Generated:** {ts}",
            f"**Platforms:** {', '.join(plan.platforms)}",
            f"**Products collected:** {len(df):,}",
            f"",
            "---",
            "",
        ]

        # Key findings (from Codex analysis or simple fallback)
        key_findings = findings.get("key_findings", [])
        if key_findings:
            lines += ["## Key Findings", ""]
            for f_item in key_findings:
                lines.append(f"- {f_item}")
            lines.append("")

        # Price summary
        if "mean_price" in findings:
            lines += [
                "## Price Summary",
                "",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Mean price | {findings['mean_price']:,} KRW |",
                f"| Median price | {findings['median_price']:,} KRW |",
                f"| Lowest | {findings['price_range']['min']:,} KRW |",
                f"| Highest | {findings['price_range']['max']:,} KRW |",
                "",
            ]

        # Price clusters
        if "price_clusters" in findings:
            lines += ["## Price Clusters", ""]
            for cluster in findings["price_clusters"]:
                lines.append(f"- {cluster}")
            lines.append("")

        # Top products by review
        if "top_by_reviews" in findings:
            lines += ["## Top Products by Review Count", ""]
            lines += ["| Title | Reviews | Price |", "|-------|---------|-------|"]
            for p in findings["top_by_reviews"]:
                title = str(p.get("title", ""))[:50]
                reviews = p.get("review_count", "-")
                price = f"{int(p['price']):,} KRW" if p.get("price") else "-"
                lines.append(f"| {title} | {reviews:,} | {price} |")
            lines.append("")

        # Per-platform breakdown
        if "platform" in df.columns:
            lines += ["## Platform Breakdown", ""]
            for platform, group in df.groupby("platform"):
                count = len(group)
                avg_price = group["price"].mean()
                avg_reviews = group["review_count"].mean()
                lines += [
                    f"### {platform.title()}",
                    f"- Products: {count:,}",
                    f"- Average price: {int(avg_price):,} KRW" if pd.notna(avg_price) else "- Average price: N/A",
                    f"- Average reviews: {avg_reviews:.0f}",
                    "",
                ]

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
