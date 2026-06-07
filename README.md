# 🛒 ShopRadar Agent

<p align="center">
  <img src="https://img.shields.io/badge/Powered%20by-GPT%20Codex-412991?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Status-In%20Development-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

<p align="center">
  <b>An agentic market research assistant for Korean e-commerce — With GPT Codex or Other Agentic AI.<br/>
  Built by a student preparing to launch a product, to make competitive analysis actually manageable.</b>
</p>

---

## 📌 Why I Built This

I'm a student working on launching a product in the Korean e-commerce space. Before building anything, I needed to answer real questions:

- What are competitors charging for similar products on Naver Shopping vs. Coupang?
- Which keywords are trending in my category right now?
- How saturated is the market, and where are the gaps?

Doing this manually — tab by tab, spreadsheet by spreadsheet — took hours and the data was already stale by the time I finished. So I started building **ShopRadar Agent**: an AI-powered tool that does the research loop for me, autonomously.

The core idea is simple: instead of hard-coding scrapers for every platform and every question, I use **GPT Codex to write and run the data collection code on the fly**, based on whatever I want to research. The agent plans, codes, executes, and summarizes — I just tell it what I want to know.

---

## 🗺️ What It Does

```
You:    "Compare wireless earphone prices under 50,000 KRW on Naver Shopping and Coupang.
         Show top 10 by review count and flag any pricing gaps."

Agent:  [PLAN]    Identify target platforms and search terms
        [CODE]    GPT Codex writes the Naver + Coupang scrapers for this query
        [RUN]     Scrapers execute, data collected
        [ANALYZE] Codex interprets results, spots patterns
        [REPORT]  Markdown + CSV report generated
        Done in ~2 minutes.
```

---

## 🧩 Core Features

### 🤖 Codex-Generated Scrapers (the main idea)
Rather than maintaining a fixed set of scrapers, the agent asks GPT Codex to write platform-specific data collection code based on the current query. This means it can adapt to new search terms, new filters, or slightly different data formats without manual updates.

### 🏪 Supported Platforms
| Platform | Data Collected |
|----------|---------------|
| **Naver Shopping** | Price, review count, seller info, keywords |
| **Coupang** | Ranking, price history, Rocket Delivery flag |
| **11번가** | Category trends, promotional pricing |
| **G마켓** | Seller competition, bundled deals |

> More platforms can be added by describing them to the agent — Codex writes the scraper.

### 📊 Automated Analysis
After collection, the agent runs a Codex-generated analysis script that produces:
- Price distribution across platforms
- Competitive density score (how many sellers, price spread)
- Keyword frequency from product titles and tags
- Basic positioning suggestions (e.g., "under-served price range: 32,000–38,000 KRW")

### 📝 Research Reports
Every run generates a structured Markdown report + raw CSV, ready to share or drop into a pitch deck.

---

## 🏗️ Project Structure

```
shopradар-agent/
├── agent/
│   ├── core.py              # Main agent loop (Plan → Code → Run → Analyze)
│   ├── planner.py           # Breaks user query into research sub-tasks
│   └── reporter.py          # Formats final output into Markdown + CSV
│
├── codex/
│   ├── scraper_gen.py       # Asks Codex to write platform scrapers
│   └── analyzer_gen.py      # Asks Codex to write analysis scripts
│
├── platforms/
│   ├── naver.py             # Naver Shopping interface
│   ├── coupang.py           # Coupang interface
│   ├── eleventh.py          # 11번가 interface
│   └── gmarket.py           # G마켓 interface
│
├── reports/                 # Auto-generated research outputs
│   └── example_report.md
│
├── notebooks/
│   └── market_exploration.ipynb   # Manual exploration + prototyping
│
├── tests/
│   └── test_agent.py
│
├── .env.example
├── config.yaml
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### Requirements
- Python 3.10+
- OpenAI API key with Codex access
- Chrome + ChromeDriver (for platforms without public APIs)

### Install

```bash
git clone https://github.com/your-username/shopradar-agent.git
cd shopradar-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
CODEX_MODEL=code-davinci-002
MAX_RESULTS_PER_PLATFORM=50
HEADLESS_BROWSER=true
REPORT_OUTPUT_DIR=./reports
```

---

## 🚀 Usage

### Basic query

```bash
python -m agent run --query "무선 이어폰 3만원 이하 네이버쇼핑 경쟁 분석"
```

### Python API

```python
from agent.core import ShopRadarAgent

agent = ShopRadarAgent()

report = agent.research(
    query="Compare protein powder prices on Coupang and Naver Shopping. "
          "Find the 20 best-reviewed products and identify price clusters.",
    platforms=["coupang", "naver"],
    max_results=20
)

print(report.summary)
report.save("./reports/protein_powder_analysis.md")
```

### Example Report Output

```markdown
## Market Research Report — Wireless Earbuds (Under 50,000 KRW)
Generated: 2025-06-07

### Key Findings
- 847 products found across 4 platforms
- Average price: 31,400 KRW (Naver), 29,800 KRW (Coupang)
- Under-served range: 38,000–45,000 KRW (few products, high review scores)
- Top keyword in titles: "노이즈캔슬링", "블루투스 5.3", "통화품질"

### Competitive Density
- High competition: under 20,000 KRW (commodity zone)
- Medium competition: 20,000–35,000 KRW
- Low competition: 38,000–45,000 KRW ← potential opportunity

### Top 5 Products by Review Count
| Product | Platform | Price | Reviews |
|---------|----------|-------|---------|
| ... | Coupang | 24,900 | 12,847 |
...
```

---

## 🗓️ Roadmap

- [x] Basic agent loop (plan → generate code → execute → report)
- [x] Naver Shopping scraper via Codex
- [x] Coupang integration
- [ ] **Price change tracking** — re-run queries over time and log changes
- [ ] **Keyword trend graphs** — visualize rising/falling search terms
- [ ] **Seller profiling** — identify key competitors in a niche
- [ ] **Alert system** — notify when a competitor drops price significantly
- [ ] **Web dashboard** — simple Streamlit UI for non-command-line use
- [ ] **Export to Google Sheets** — for team sharing during business planning

---

## 🎓 Learning Goals

This project is also my way of learning:

- How LLM-based agents actually work (planning loops, tool use, self-correction)
- How GPT Codex can generate task-specific code rather than just answering questions
- Practical web data collection from Korean e-commerce platforms
- Turning raw scraped data into actionable business insights

I'm documenting what I learn in [`/notebooks`](./notebooks) and plan to write up the experience once the project matures.

---

## 📋 Requirements

```
openai>=1.0.0
selenium>=4.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
pandas>=2.0.0
matplotlib>=3.7.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

---

## ⚠️ Responsible Use

This project is for **personal research and learning purposes only**. When collecting data:
- Respect each platform's `robots.txt` and terms of service
- Use reasonable request delays to avoid overloading servers
- Do not scrape personal user data
- Data collected is used only for market research, not redistributed

---

## 🤝 Contributing

This is a solo student project, but I'm open to suggestions. If you're working on something similar or have ideas, feel free to open an issue.

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgements

- [OpenAI](https://openai.com) for GPT Codex, which makes the "generate the scraper at runtime" approach possible
- The [ReAct paper](https://arxiv.org/abs/2210.03629) for the agent loop framework
- Korean e-commerce research communities for inspiration on what to measure

---

<p align="center">
  Built while studying · Learning by shipping · Powered by GPT Codex
</p>
