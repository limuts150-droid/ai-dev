"""
analyzer_gen.py — Ask Codex to write analysis code based on collected data.

Same approach as scraper_gen: describe the dataset and the research question,
let Codex write the analysis script, execute it, parse the output.

This part actually works quite well even with the fallback model because
analysis code (pandas, basic stats) is more standard than scraping code.
"""

import os
import json
import logging
import textwrap
from typing import Optional

import openai
import pandas as pd
from dotenv import load_dotenv

from .scraper_gen import run_generated_code, _call_chat_fallback, _call_codex

load_dotenv()
logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM = "You are a data analyst. Write Python code using pandas. Output only code."

ANALYSIS_PROMPT = textwrap.dedent("""
# Task: Analyze this e-commerce dataset and answer the research question.

Dataset columns: {columns}
Number of rows: {n_rows}
Research question: {question}

The data is in a file called 'data.csv'.

Write a script that:
1. Loads the CSV
2. Computes statistics relevant to the question
3. Identifies price clusters if a 'price' column exists
4. Prints a JSON summary at the end with keys:
   - mean_price, median_price, price_range (min, max)
   - top_sellers (list of seller names by product count, top 5)
   - price_clusters (list of cluster ranges, e.g. ["0-20000", "20000-40000"])
   - key_findings (list of 2-3 plain-language insights)

Write only Python code, no explanation.
""").strip()


def generate_analysis(df: pd.DataFrame, question: str) -> Optional[dict]:
    """
    Given a DataFrame of scraped products and a research question,
    ask Codex to write and run an analysis script.

    Returns a dict of findings or None on failure.
    """
    import tempfile

    # Save df to a temp CSV so the generated script can read it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, dir=".") as f:
        df.to_csv(f, index=False)
        tmp_csv = f.name

    # Rename to data.csv in CWD since the prompt hardcodes that name
    os.rename(tmp_csv, "data.csv")

    prompt = ANALYSIS_PROMPT.format(
        columns=", ".join(df.columns.tolist()),
        n_rows=len(df),
        question=question,
    )

    try:
        code = _call_codex(prompt)
    except Exception:
        logger.warning("Codex unavailable for analysis, using fallback")
        code = _call_chat_fallback(prompt)

    if not code:
        return None

    output = run_generated_code(code, timeout=30)

    if not output:
        return None

    # Find the JSON block in stdout
    try:
        # Codex sometimes adds explanation after the JSON - grab just the JSON
        json_start = output.find("{")
        json_end   = output.rfind("}") + 1
        return json.loads(output[json_start:json_end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Could not parse analysis output as JSON: {e}")
        logger.debug(f"Raw output was:\n{output[:500]}")
        return None
    finally:
        if os.path.exists("data.csv"):
            os.remove("data.csv")


def simple_analysis(df: pd.DataFrame) -> dict:
    """
    Fallback analysis using pure pandas (no Codex needed).
    Less flexible than Codex-generated code but always works.
    """
    result: dict = {}

    if "price" in df.columns:
        prices = df["price"].dropna()
        result["mean_price"]   = int(prices.mean())
        result["median_price"] = int(prices.median())
        result["price_range"]  = {"min": int(prices.min()), "max": int(prices.max())}

        # Rough price clustering (quartile-based)
        q1, q2, q3 = prices.quantile([0.25, 0.5, 0.75])
        result["price_clusters"] = [
            f"0 – {int(q1):,}",
            f"{int(q1):,} – {int(q2):,}",
            f"{int(q2):,} – {int(q3):,}",
            f"{int(q3):,}+",
        ]

    if "review_count" in df.columns:
        result["total_reviews"]   = int(df["review_count"].sum())
        result["avg_reviews"]     = round(df["review_count"].mean(), 1)
        top = df.nlargest(5, "review_count")[["title", "review_count", "price"]]
        result["top_by_reviews"]  = top.to_dict(orient="records")

    if "seller" in df.columns:
        result["top_sellers"] = (
            df["seller"].value_counts().head(5).to_dict()
        )

    return result
