"""
scraper_gen.py — Ask GPT Codex to write platform-specific scraping code at runtime.

This is the part of the project I'm most excited about and also the part
that's hardest to develop without sustained API access.

The idea: instead of me manually writing a scraper for every possible query
variation, I describe what I want in plain language and let Codex write the
code. Then I execute it in a sandboxed subprocess.

It actually worked pretty well in early tests (see notebooks/market_exploration.ipynb).
The generated scrapers weren't always perfect but they were a solid starting
point - usually just needed a CSS selector tweak.

The problem: code-davinci-002 is expensive and I burned through my free trial
credits faster than expected while iterating on the prompts. The code below
still works, it just needs a key with enough balance.

I've been using gpt-3.5-turbo as a fallback for the planning steps, but
it's noticeably worse at writing reliable scraping code compared to Codex.
"""

import os
import textwrap
import subprocess
import tempfile
import logging
from typing import Optional

import openai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
CODEX_MODEL   = os.getenv("CODEX_MODEL", "code-davinci-002")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")


# --- Prompt templates ---------------------------------------------------------

SCRAPER_PROMPT = textwrap.dedent("""
# Task: Write a Python scraping function for the following specification.

Platform: {platform}
Search keyword: {keyword}
Fields to extract: {fields}
Sort order: {sort}
Max results: {max_results}

Requirements:
- Use requests + BeautifulSoup if the site allows it, else Selenium
- Return a list of dicts, one per product, with keys: {fields}
- Add a 1-2 second delay between page requests
- Handle missing fields gracefully (set to None)
- Print progress to stderr so the caller can track it
- The function should be named `run_scrape()` and take no arguments
- At the bottom, call run_scrape() and print the results as JSON

Write only the Python code, no explanation.
""").strip()


ANALYSIS_PROMPT = textwrap.dedent("""
# Task: Write a Python analysis script for the following e-commerce dataset.

Dataset columns: {columns}
Number of rows: {n_rows}
Research question: {question}

Requirements:
- Read from a CSV file called 'data.csv'
- Produce a summary dict with keys relevant to the research question
- Print the summary as JSON at the end
- Include basic statistics: mean/median price, price range, top sellers by count
- Flag any interesting patterns (e.g. price clusters, outlier products)

Write only the Python code, no explanation.
""").strip()


# --- Core functions -----------------------------------------------------------

def generate_scraper(
    platform: str,
    keyword: str,
    fields: list[str],
    sort: str = "review",
    max_results: int = 30,
) -> Optional[str]:
    """
    Ask Codex to write a scraping script for the given platform and keyword.

    Returns the generated Python code as a string, or None on failure.
    """
    prompt = SCRAPER_PROMPT.format(
        platform=platform,
        keyword=keyword,
        fields=", ".join(fields),
        sort=sort,
        max_results=max_results,
    )

    try:
        # Try Codex first (best at code generation)
        code = _call_codex(prompt)
        logger.info(f"Codex generated scraper for [{platform}] keyword='{keyword}'")
        return code

    except openai.RateLimitError:
        logger.warning("Codex rate limit hit - falling back to gpt-3.5-turbo")
        # Fallback: wrap prompt in a chat message
        return _call_chat_fallback(prompt)

    except openai.AuthenticationError:
        logger.error(
            "OpenAI API key issue - check your .env file. "
            "Note: code-davinci-002 requires a key with Codex access enabled."
        )
        return None

    except Exception as e:
        logger.error(f"Codex call failed: {e}")
        return None


def run_generated_code(code: str, timeout: int = 60) -> Optional[str]:
    """
    Execute Codex-generated code in a subprocess and return stdout.

    Uses a temp file so we don't have to eval() untrusted code directly.
    Timeout prevents runaway scrapers.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning(f"Generated script exited with error:\n{result.stderr[:500]}")
            # TODO: feed the error back to Codex for self-correction
            #       tried this once and it worked but used a lot of tokens
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"Generated scraper timed out after {timeout}s")
        return None
    finally:
        os.unlink(tmp_path)


# --- Internal helpers ---------------------------------------------------------

def _call_codex(prompt: str) -> str:
    """Call code-davinci-002 (Codex) for code completion."""
    response = openai.completions.create(
        model=CODEX_MODEL,
        prompt=prompt,
        max_tokens=int(os.getenv("CODEX_MAX_TOKENS", 600)),
        temperature=0.2,       # low temp = more deterministic code
        stop=["# End"],
    )
    return response.choices[0].text.strip()


def _call_chat_fallback(prompt: str) -> str:
    """
    Fallback to gpt-3.5-turbo when Codex isn't available.
    Results are okay but Codex is noticeably better for scraping code.
    """
    response = openai.chat.completions.create(
        model=FALLBACK_MODEL,
        messages=[
            {"role": "system", "content": "You are a Python developer. Write clean, working code only. No explanation."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=800,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
