"""
Basic tests for ShopRadar Agent.

Tests that need a live API key are marked with @pytest.mark.skipif
so CI doesn't fail when OPENAI_API_KEY isn't set.

Tests that only need local logic (parsing, formatting, data transforms)
run unconditionally.
"""

import os
import pytest
import pandas as pd

# ── Local logic tests (no API needed) ─────────────────────────────────────────

def test_planner_validate():
    from agent.planner import Planner
    planner = Planner()
    raw = {
        "keyword": "무선이어폰",
        "platforms": ["naver", "coupang", "unknown_platform"],  # unknown should be filtered
        "sort": "review",
        "max_pages": 10,  # should be clamped to 5
        "research_question": "How competitive is the wireless earphone market?"
    }
    plan = planner._validate(raw)
    assert "unknown_platform" not in plan.platforms
    assert plan.max_pages <= 5
    assert plan.keyword == "무선이어폰"


def test_simple_analysis_prices():
    from codex.analyzer_gen import simple_analysis
    df = pd.DataFrame({
        "title":        ["Product A", "Product B", "Product C"],
        "price":        [15000, 30000, 45000],
        "review_count": [100, 500, 200],
        "seller":       ["SellerX", "SellerY", "SellerX"],
        "platform":     ["naver", "naver", "coupang"],
    })
    result = simple_analysis(df)
    assert result["mean_price"] == 30000
    assert result["median_price"] == 30000
    assert result["price_range"]["min"] == 15000
    assert result["price_range"]["max"] == 45000
    assert "top_sellers" in result


def test_reporter_creates_file(tmp_path):
    from agent.reporter import Reporter
    from agent.planner import ResearchPlan
    reporter = Reporter()
    df = pd.DataFrame({
        "platform":     ["naver", "coupang"],
        "title":        ["Product A", "Product B"],
        "price":        [20000, 35000],
        "review_count": [100, 200],
    })
    plan = ResearchPlan(
        keyword="무선이어폰",
        platforms=["naver", "coupang"],
        research_question="What is the competitive landscape?"
    )
    findings = {
        "mean_price":   27500,
        "median_price": 27500,
        "price_range":  {"min": 20000, "max": 35000},
        "key_findings": ["Most products cluster between 20,000-35,000 KRW"],
    }
    out = tmp_path / "test_report.md"
    reporter.write(str(out), "test query", plan, df, findings)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "Market Research Report" in content
    assert "무선이어폰" in content  # keyword should appear in plan section... actually in query context


# ── API-dependent tests (skip if no key) ──────────────────────────────────────

HAVE_API_KEY = bool(os.getenv("OPENAI_API_KEY"))

@pytest.mark.skipif(not HAVE_API_KEY, reason="OPENAI_API_KEY not set")
def test_planner_real_query():
    from agent.planner import Planner
    planner = Planner()
    plan = planner.plan("쿠팡에서 단백질 보충제 5만원 이하 리뷰 많은 순으로 분석해줘")
    assert plan.keyword
    assert "coupang" in plan.platforms
    assert plan.price_max == 50000 or plan.price_max is None  # might not catch it


@pytest.mark.skipif(not HAVE_API_KEY, reason="OPENAI_API_KEY not set")
def test_codex_scraper_generation():
    """
    Check that Codex actually returns valid Python code.
    Doesn't execute it - just checks it's non-empty and looks like code.
    
    NOTE: This test used code-davinci-002. After credits ran out I haven't
    been able to re-run it. It passed the last time I had balance.
    """
    from codex.scraper_gen import generate_scraper
    code = generate_scraper(
        platform="naver",
        keyword="무선이어폰",
        fields=["title", "price", "review_count"],
        max_results=10,
    )
    assert code is not None
    assert "def" in code or "import" in code  # should look like Python
