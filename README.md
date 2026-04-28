# grad-scout

A LangGraph agent that automates graduate program research. Given your field, country preferences, and budget, it searches mastersportal.eu, visits each university's program page, extracts requirements and deadlines, and returns a ranked comparison table — in minutes instead of hours.

## The Problem

Manually researching master's and PhD programs across European universities is slow:
- Filter on aggregator sites → get a list of 30+ programs
- Click each program → visit the university website
- Manually read requirements, deadlines, fees on each page
- Copy relevant info into a spreadsheet

This takes **1+ hour per 3 programs**. grad-scout automates the entire pipeline.

## Architecture

```
User constraints
      ↓
[intake] → [discover] → [research loop] → [rank] → [output]
                              ↑___|
                         (one page per iteration)
```

| Node | What it does |
|------|-------------|
| **intake** | Validates your constraints (field, countries, fees, language, level) |
| **discover** | Playwright → mastersportal.eu → list of matching programs |
| **research** | Per program: visits university page → LLM extracts structured info |
| **rank** | Scores each program against your constraints (fees, language, deadline, country) |
| **output** | Ranked markdown table + JSON export |

### LLM Strategy

Two models, selected by task:

| Task | Model | Why |
|------|-------|-----|
| HTML extraction (runs per program) | `llama-3.1-8b-instant` | Fast, stays within Groq rate limits |
| Ranking & reasoning (runs once) | `llama-3.3-70b-versatile` | Better reasoning for scoring |

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/esrabrahmii/grad-scout
cd grad-scout
pip install -e ".[dev]"
playwright install chromium

# 2. Configure
cp .env.example .env
# Add your GROQ_API_KEY to .env (free at console.groq.com)

# 3. Run the UI
make ui
# → opens at localhost:8501

# 4. Or use the CLI
make search
```

## Example Output

| # | Program | University | Country | Fees | Deadline | Score |
|---|---------|------------|---------|------|----------|-------|
| 1 | MSc Artificial Intelligence | TU Berlin | Germany | Free | 15 May 2026 | 95/100 |
| 2 | MSc Data Science & AI | Eindhoven University | Netherlands | Free (EU) | 1 Apr 2026 | 88/100 |
| 3 | MSc Machine Learning | KTH Royal Institute | Sweden | Free | 15 Jan 2026 | 82/100 |

## Tech Stack

- **LangGraph** — stateful agent with research loop and conditional edges
- **Playwright** — headless Chromium for JS-rendered university pages
- **LangChain + Groq** — structured LLM output (Pydantic schema extraction)
- **BeautifulSoup** — HTML cleaning before LLM extraction
- **Streamlit** — interactive UI with progress tracking and export
- **Pydantic v2** — typed models for all data (constraints, programs, scores)

## Configuration

All settings via `.env`:

```bash
GROQ_API_KEY=gsk_...              # Required
LLM_PROVIDER=groq                 # groq or openai
EXTRACTION_MODEL=llama-3.1-8b-instant
REASONING_MODEL=llama-3.3-70b-versatile
HEADLESS=true                     # false = watch the browser
MAX_PROGRAMS=30
REQUEST_DELAY_SECONDS=1.5         # polite delay between page loads
```

## Makefile

```bash
make install          # pip install -e ".[dev]"
make install-browsers # playwright install chromium
make ui               # streamlit run app/main.py
make search           # CLI interactive mode
make test             # pytest
make lint             # ruff check
make typecheck        # mypy
```
