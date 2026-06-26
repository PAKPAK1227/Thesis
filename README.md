# Thesis — AI-Powered Equity Research Platform

Thesis is an AI-powered equity research platform that helps users explore public companies through market data, financial fundamentals, recent news, interactive price charts, and AI-generated research memos.

It combines structured financial data with recent news context to produce balanced, beginner-friendly company analysis without providing direct investment recommendations.

## Features

- Search and analyze publicly traded companies by ticker symbol
- View company fundamentals, including market capitalization, P/E ratios, revenue growth, profit margins, and 52-week range
- Explore historical stock-price performance across multiple time ranges
- Generate AI-powered investment memos with:
  - Executive summary
  - Investment thesis
  - Key catalysts
  - Financial snapshot
  - Risk factors
  - Bull, base, and bear scenarios
- Compare two companies side by side
- Generate AI comparison memos covering valuation, financials, strengths, risks, and investor-profile considerations
- View a live market snapshot for major U.S. indexes
- Display recent company news alongside analysis
- Handle missing API keys, rate limits, and temporary AI-service failures gracefully

## Tech Stack

**Language**
- Python

**Frameworks and Libraries**
- Streamlit
- Altair
- yfinance
- OpenAI Python SDK
- python-dotenv

**Engineering Tools**
- Git and GitHub
- pytest
- Virtual environments

## Architecture

The project separates user-interface code from reusable business logic:

```text
app.py
├── Streamlit interface
├── User inputs and visual rendering
├── Market-data fetching
└── AI memo display and error handling

logic.py
├── Ticker and market-data processing
├── Financial formatting
├── News parsing
├── Prompt construction
├── Memo parsing
└── Reusable calculation helpers

tests/test_logic.py
└── Unit tests for core business logic

```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/PAKPAK1227/Thesis.git
cd Thesis
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a file named `.env` in the project root:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not commit `.env` to GitHub. Use `.env.example` as a safe reference.

### 5. Run the application

```bash
streamlit run app.py
```

## Running Tests

Install pytest if needed:

```bash
python -m pip install pytest
```

Then run:

```bash
python -m pytest -q
```

## Disclaimer

Thesis is an educational research tool and does not provide financial, investment, tax, or legal advice. AI-generated content should be independently reviewed before making financial decisions.

## Future Improvements

* User accounts and saved watchlists
* Portfolio-level analytics
* Expanded market-data sources
* Research-history storage
* Exportable research reports
* More advanced company and sector comparisons
