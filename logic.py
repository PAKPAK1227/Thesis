"""Pure business logic for the Thesis equity-research app.

This module deliberately contains **no Streamlit / UI code**. Everything here
is a pure function (data in, data out) or a thin wrapper around an injected
client, so it can be unit-tested without a browser, a network connection, or a
running OpenAI / yfinance session.

app.py is responsible for the visuals; this module is responsible for the
calculations, text building, prompt construction and parsing.
"""

import re
import html


# --- Constants ------------------------------------------------------------

# Human-friendly labels for the selected period.
PERIOD_LABELS = {
    "1mo": "the Last Month",
    "3mo": "the Last 3 Months",
    "6mo": "the Last 6 Months",
    "1y":  "the Last Year",
}

MARKET_INDEXES = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
}

# Colour assigned to each AI-memo section header.
SECTION_COLORS = {
    "Executive Summary":  "#60A5FA",
    "Investment Thesis":  "#A78BFA",
    "Key Catalysts":      "#34D399",
    "Financial Snapshot": "#94A3B8",
    "Risk Factors":       "#FBBF24",
    "Bull Case":          "#22C55E",
    "Base Case":          "#94A3B8",
    "Bear Case":          "#EF4444",
    "Conclusion":         "#60A5FA",
    "Executive Comparison":              "#60A5FA",
    "Valuation and Financial Comparison": "#A78BFA",
    "Key Strengths":                     "#34D399",
    "Key Risks":                         "#FBBF24",
    "Investor Profile Considerations":   "#94A3B8",
}

DEFAULT_SECTION_COLOR = "#94A3B8"

NA = "N/A"


# --- Ticker / history -----------------------------------------------------

def clean_ticker(raw):
    """Normalise a user-entered ticker to upper-case with no surrounding space."""
    if not raw:
        return ""
    return raw.upper().strip()


def is_valid_history(history):
    """Return True when a yfinance history DataFrame actually contains rows."""
    return history is not None and not history.empty


def price_stats(history):
    """Compute highest / lowest / average closing price from a history frame."""
    closes = history["Close"]
    return {
        "highest": closes.max(),
        "lowest":  closes.min(),
        "average": closes.mean(),
    }


def market_snapshot_from_histories(histories):
    """Build latest close and daily percentage-change data for major indices."""
    snapshot = []

    for label, symbol in MARKET_INDEXES.items():
        history = histories.get(symbol)

        if not is_valid_history(history) or "Close" not in history:
            snapshot.append({
                "label": label,
                "symbol": symbol,
                "close": None,
                "change_pct": None,
            })
            continue

        closes = history["Close"].dropna()

        if len(closes) < 2:
            snapshot.append({
                "label": label,
                "symbol": symbol,
                "close": None,
                "change_pct": None,
            })
            continue

        latest_close = float(closes.iloc[-1])
        previous_close = float(closes.iloc[-2])
        change_pct = ((latest_close - previous_close) / previous_close) * 100

        snapshot.append({
            "label": label,
            "symbol": symbol,
            "close": latest_close,
            "change_pct": change_pct,
        })

    return snapshot


def period_label(period):
    """Human-friendly label for a period code, falling back to the code itself."""
    return PERIOD_LABELS.get(period, period)


# --- Fundamentals / info --------------------------------------------------

def extract_info(info, ticker_fallback=None):
    """Pull the fields used by the UI out of a yfinance ``info`` dict.

    Missing fields default to ``"N/A"`` (the long name optionally falls back to
    the ticker symbol, mirroring the comparison section).
    """
    info = info or {}
    name_fallback = ticker_fallback if ticker_fallback else NA
    return {
        "company_name":        info.get("longName",         name_fallback),
        "sector":              info.get("sector",           NA),
        "current_price":       info.get("currentPrice",     NA),
        "market_cap":          info.get("marketCap",        NA),
        "trailing_pe":         info.get("trailingPE",       NA),
        "forward_pe":          info.get("forwardPE",        NA),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh", NA),
        "fifty_two_week_low":  info.get("fiftyTwoWeekLow",  NA),
        "profit_margins":      info.get("profitMargins",    NA),
        "revenue_growth":      info.get("revenueGrowth",    NA),
    }


def build_fundamentals_text(extracted):
    """Build the fundamentals block fed to the AI prompt from extract_info()."""
    return (
        f"\n        Trailing P/E: {extracted['trailing_pe']}"
        f"\n        Forward P/E: {extracted['forward_pe']}"
        f"\n        52-Week High: {extracted['fifty_two_week_high']}"
        f"\n        52-Week Low: {extracted['fifty_two_week_low']}"
        f"\n        Profit Margins: {extracted['profit_margins']}"
        f"\n        Revenue Growth: {extracted['revenue_growth']}\n        "
    )


# --- News -----------------------------------------------------------------

def parse_news_items(news, limit=5):
    """Normalise raw yfinance news into a list of display-ready dicts."""
    items = []
    for article in (news or [])[:limit]:
        content = article.get("content", {})
        items.append({
            "title":    content.get("title",   "No title"),
            "summary":  content.get("summary", "No summary available"),
            "pub_date": content.get("pubDate", "No date available"),
            "url":      (content.get("canonicalUrl", {}) or {}).get("url", "") or "",
        })
    return items


def build_news_text(news, limit=5):
    """Build the plain-text news block fed to the AI prompt."""
    news_text = ""
    for article in (news or [])[:limit]:
        content = article.get("content", {})
        title   = content.get("title",   "No title")
        summary = content.get("summary", "No summary available")
        news_text += f"Title: {title}\nSummary: {summary}\n\n"
    return news_text


# --- Formatting helpers ---------------------------------------------------

def format_price(value):
    """Format a price as ``$1,234.56`` or ``N/A`` when unavailable."""
    if value == NA or value is None:
        return NA
    return f"${value:,.2f}"


def format_market_cap_trillions(value):
    """Format market cap in trillions, e.g. ``$2.40T``."""
    if value == NA or value is None:
        return NA
    return f"${value / 1_000_000_000_000:.2f}T"


def format_pe(value):
    """Format a P/E multiple as ``12.3x`` or pass the raw value through."""
    if isinstance(value, (int, float)):
        return f"{value:.1f}x"
    return str(value)


def format_percent_signed(value):
    """Return ``(text, positive)`` for a fractional value like ``0.123``.

    Returns ``(None, None)`` when the value is unavailable.
    """
    if value == NA or value is None:
        return None, None
    pct = value * 100
    return f"{abs(pct):.1f}%", pct >= 0


def format_52w_range(low, high):
    """Format a 52-week range string, or ``N/A`` if either bound is missing."""
    if low == NA or high == NA or low is None or high is None:
        return NA
    return f"${low:.2f} – ${high:.2f}"


# --- AI memo --------------------------------------------------------------

def build_memo_prompt(*, company_name, ticker, sector, current_price, market_cap,
                      period, highest_close, lowest_close, avg_close,
                      fundamentals_text, news_text):
    """Construct the investment-memo prompt sent to the model."""
    return f"""
        You are an investment research analyst.

        Analyze the company below using only the provided market data and recent news.
        Do not give direct financial advice. Do not tell the user to buy, sell, or hold.
        Write in a professional but beginner-friendly tone.

        Company: {company_name}
        Ticker: {ticker}
        Sector: {sector}
        Current Price: {current_price}
        Market Cap: {market_cap}
        Selected Time Period: {period_label(period)}
        Highest Close: {highest_close}
        Lowest Close: {lowest_close}
        Average Close: {avg_close}

        Fundamentals:
        {fundamentals_text}

        Recent News:
        {news_text}

        Provide the output in this exact structure:

        ### Executive Summary
        Provide a concise 2-3 sentence overview of the company's current situation based on the fundamentals and recent news.

        ### Investment Thesis
        Explain the primary reason the company could outperform over the medium to long term.

        ### Key Catalysts
        List 3-5 positive developments or events that could drive future growth.

        ### Financial Snapshot
        Discuss:
        - Valuation (P/E ratios)
        - Revenue growth
        - Profitability
        - Current price relative to the 52-week range
        - Any notable trends in the stock's recent performance

        ### Risk Factors
        List 3-5 major risks investors should monitor.

        ### Bull Case
        Describe the strongest optimistic scenario for the company.

        ### Base Case
        Describe the most likely outcome if the company continues performing in line with expectations.

        ### Bear Case
        Describe the strongest pessimistic scenario for the company.

        ### Conclusion
        Provide a final 2-3 sentence summary of the company's overall investment narrative.

        Formatting Requirements:
        - Never use dollar signs ($).
        - Write all currency values using USD.
        - Example: USD 297.55 instead of $297.55.
        - Do not use markdown emphasis or italics.

        Important:
        - Use professional but accessible language.
        - Reference specific numbers from the provided fundamentals whenever relevant.
        - Focus on analysis rather than simply repeating the news.
        - Do not provide a buy, sell, or hold recommendation.
        """


def build_comparison_prompt(
    *,
    company_name1,
    ticker1,
    sector1,
    fundamentals_text1,
    news_text1,
    average_close1,
    company_name2,
    ticker2,
    sector2,
    fundamentals_text2,
    news_text2,
    average_close2,
    period,
):
    """Construct a balanced side-by-side investment comparison prompt."""
    return f"""
        You are an investment research analyst.

        Compare the two companies below using only the provided fundamentals,
        market data, and recent news. Do not give direct financial advice.
        Do not tell the user to buy, sell, or hold either stock.

        Write in a professional but beginner-friendly tone.

        Company One:
        Name: {company_name1}
        Ticker: {ticker1}
        Sector: {sector1}
        Average Closing Price During {period_label(period)}: {average_close1}

        Fundamentals:
        {fundamentals_text1}

        Recent News:
        {news_text1}

        Company Two:
        Name: {company_name2}
        Ticker: {ticker2}
        Sector: {sector2}
        Average Closing Price During {period_label(period)}: {average_close2}

        Fundamentals:
        {fundamentals_text2}

        Recent News:
        {news_text2}

        Provide the output in this exact structure:

        ### Executive Comparison
        Give a concise overview of how the two companies differ in business profile,
        financial position, and recent market narrative.

        ### Valuation and Financial Comparison
        Compare valuation, revenue growth, profitability, and stock performance.

        ### Key Strengths
        List the strongest qualities of each company.

        ### Key Risks
        List the most important risks for each company.

        ### Investor Profile Considerations
        Explain what type of investor priorities each company may align with,
        such as growth, stability, value, or higher-risk opportunities.
        Do not recommend either company.

        ### Conclusion
        Give a balanced final summary of the major trade-offs between the two companies.

        Formatting Requirements:
        - Never use dollar signs ($).
        - Write currency values using USD.
        - Do not use markdown emphasis or italics.
        - Use headings exactly as written above.
        - Focus on comparison, not separate standalone analyses.
    """


def generate_memo(client, prompt, model="gpt-5-mini"):
    """Run the prompt through the injected OpenAI client and return the text."""
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def md_to_html(text):
    """Convert bullet/numbered lists and paragraphs to HTML for memo cards."""
    lines = text.split('\n')
    out = []
    in_ul = in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append('</ul>'); in_ul = False
        if in_ol:
            out.append('</ol>'); in_ol = False

    def fmt(s):
        s = html.escape(s, quote=False)
        s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
        return s

    for line in lines:
        s = line.strip()
        if not s:
            close_lists()
            continue
        if s.startswith('- ') or s.startswith('• '):
            if in_ol:
                out.append('</ol>'); in_ol = False
            if not in_ul:
                out.append('<ul style="margin:8px 0;padding-left:20px;">')
                in_ul = True
            out.append(f'<li style="margin:3px 0;line-height:1.6;">{fmt(s[2:])}</li>')
        elif re.match(r'^\d+\.\s', s):
            if in_ul:
                out.append('</ul>'); in_ul = False
            if not in_ol:
                out.append('<ol style="margin:8px 0;padding-left:20px;">')
                in_ol = True
            out.append(f'<li style="margin:3px 0;line-height:1.6;">{fmt(re.sub(r"^\d+\.\s*", "", s))}</li>')
        else:
            close_lists()
            out.append(f'<p style="margin:6px 0;line-height:1.6;">{fmt(s)}</p>')

    close_lists()
    return '\n'.join(out)


def parse_memo_sections(analysis):
    """Split an AI memo into sections, each with header, body and colour."""
    sections = []
    parts = re.split(r'\n(?=### )', analysis.strip())
    for part in parts:
        if not part.strip():
            continue
        lines = part.strip().split('\n', 1)
        header = lines[0].lstrip('#').strip()
        body   = lines[1].strip() if len(lines) > 1 else ""
        sections.append({
            "header": header,
            "body":   body,
            "color":  SECTION_COLORS.get(header, DEFAULT_SECTION_COLOR),
        })
    return sections
