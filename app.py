import re
import html
import time
import streamlit as st
import yfinance as yf
import altair as alt
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Page setup -----------------------------------------------------------
st.set_page_config(
    page_title="Thesis",
    page_icon="📈",
    layout="wide",
)


# --- Helpers --------------------------------------------------------------

def metric_card(label, value, positive=None):
    if positive is True:
        color, prefix = "#22C55E", "▲ "
    elif positive is False:
        color, prefix = "#EF4444", "▼ "
    else:
        color, prefix = "inherit", ""

    st.markdown(
        f"""
        <div style="border:1px solid rgba(128,128,128,0.2);border-radius:8px;padding:16px 20px;">
            <div style="font-size:0.875rem;opacity:0.65;margin-bottom:6px;font-weight:500;">{label}</div>
            <div style="font-size:1.5rem;font-weight:700;color:{color};letter-spacing:-0.02em;">{prefix}{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def green_line_chart(df, height=300):
    return (
        alt.Chart(df)
        .mark_line(color="#22C55E", strokeWidth=2)
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(title="")),
            y=alt.Y("Close:Q", axis=alt.Axis(title="Closing Price (USD)")),
        )
        .properties(height=height)
    )


def news_card(title, pub_date, summary, url=""):
    safe_title   = html.escape(title)
    safe_summary = html.escape(summary)
    safe_date    = html.escape(pub_date)

    link_html = (
        f'<a href="{url}" target="_blank" '
        f'style="color:#22C55E;font-size:0.875rem;text-decoration:none;font-weight:500;">Read More →</a>'
        if url else ""
    )
    bottom_margin = "14px" if link_html else "0"

    st.markdown(
        f"""
        <div style="border:1px solid rgba(128,128,128,0.25);border-radius:8px;
                    padding:20px 24px;margin-bottom:12px;">
            <div style="font-weight:600;font-size:1rem;margin-bottom:6px;line-height:1.4;">{safe_title}</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.45);margin-bottom:12px;">{safe_date}</div>
            <div style="font-size:0.9rem;color:rgba(255,255,255,0.8);line-height:1.5;
                        margin-bottom:{bottom_margin};">{safe_summary}</div>
            {link_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _md_to_html(text: str) -> str:
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

    def fmt(s: str) -> str:
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


def render_styled_memo(analysis: str):
    """Parse the AI memo and render each section as a color-coded card."""
    section_colors = {
        "Executive Summary":  "#60A5FA",
        "Investment Thesis":  "#A78BFA",
        "Key Catalysts":      "#34D399",
        "Financial Snapshot": "#94A3B8",
        "Risk Factors":       "#FBBF24",
        "Bull Case":          "#22C55E",
        "Base Case":          "#94A3B8",
        "Bear Case":          "#EF4444",
        "Conclusion":         "#60A5FA",
    }

    parts = re.split(r'\n(?=### )', analysis.strip())

    for part in parts:
        if not part.strip():
            continue
        lines = part.strip().split('\n', 1)
        header = lines[0].lstrip('#').strip()
        body   = lines[1].strip() if len(lines) > 1 else ""
        color  = section_colors.get(header, "#94A3B8")
        body_html = _md_to_html(body) if body else ""

        st.markdown(
            f"""
            <div style="border:1px solid {color};border-left:4px solid {color};border-radius:8px;
                        padding:20px 24px;margin-bottom:14px;background:rgba(255,255,255,0.02);">
                <div style="font-size:1rem;font-weight:700;color:{color};margin-bottom:10px;">
                    {html.escape(header)}
                </div>
                <div style="color:rgba(255,255,255,0.85);font-size:0.92rem;">{body_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- Sidebar --------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="padding:8px 0 20px 0;">
            <div style="font-size:1.4rem;font-weight:800;letter-spacing:-0.02em;">📈 Thesis</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.45);margin-top:2px;">
                AI-Powered Equity Research
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.header("Search")
    ticker  = st.text_input("Stock ticker", placeholder="e.g. AAPL")
    ticker2 = st.text_input("Comparison ticker optional", placeholder="e.g. MSFT")

    period = st.selectbox(
        "Time Range",
        ["1mo", "3mo", "6mo", "1y"],
    )

    st.caption("Thesis generates AI-powered investment research using market data, fundamentals, and recent news.")


# Human-friendly labels for the selected period
period_labels = {
    "1mo": "the Last Month",
    "3mo": "the Last 3 Months",
    "6mo": "the Last 6 Months",
    "1y":  "the Last Year",
}

if ticker:
    ticker = ticker.upper().strip()
    stock   = yf.Ticker(ticker)
    history = stock.history(period=period)

    if history.empty:
        st.error("Invalid ticker. Please double-check the symbol and try again.")
    else:
        info = stock.info

        company_name       = info.get("longName",        "N/A")
        sector             = info.get("sector",          "N/A")
        current_price      = info.get("currentPrice",    "N/A")
        market_cap         = info.get("marketCap",       "N/A")
        trailing_pe        = info.get("trailingPE",      "N/A")
        forward_pe         = info.get("forwardPE",       "N/A")
        fifty_two_week_high = info.get("fiftyTwoWeekHigh", "N/A")
        fifty_two_week_low  = info.get("fiftyTwoWeekLow",  "N/A")
        profit_margins     = info.get("profitMargins",   "N/A")
        revenue_growth     = info.get("revenueGrowth",   "N/A")

        highest_close = history["Close"].max()
        lowest_close  = history["Close"].min()
        avg_close     = history["Close"].mean()

        fundamentals_text = f"""
        Trailing P/E: {trailing_pe}
        Forward P/E: {forward_pe}
        52-Week High: {fifty_two_week_high}
        52-Week Low: {fifty_two_week_low}
        Profit Margins: {profit_margins}
        Revenue Growth: {revenue_growth}
        """

        # --- Company header -----------------------------------------------
        st.title(f"{company_name} ({ticker})")
        st.caption(f"Sector: {sector}")

        # --- KPI cards ----------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            price_val = f"${current_price:,.2f}" if current_price != "N/A" else "N/A"
            metric_card("Price", price_val)

        with c2:
            if market_cap != "N/A":
                metric_card("Market Cap", f"${market_cap / 1_000_000_000_000:.2f}T")
            else:
                metric_card("Market Cap", "N/A")

        with c3:
            if revenue_growth != "N/A":
                rg = revenue_growth * 100
                metric_card("Revenue Growth", f"{abs(rg):.1f}%", positive=(rg >= 0))
            else:
                metric_card("Revenue Growth", "N/A")

        with c4:
            if profit_margins != "N/A":
                pm = profit_margins * 100
                metric_card("Profit Margin", f"{abs(pm):.1f}%", positive=(pm >= 0))
            else:
                metric_card("Profit Margin", "N/A")

        st.divider()

        # --- Financial Snapshot -------------------------------------------
        st.subheader("Financial Snapshot")

        f1, f2, f3 = st.columns(3)

        with f1:
            pe_str = f"{trailing_pe:.1f}x" if isinstance(trailing_pe, (int, float)) else str(trailing_pe)
            metric_card("Trailing P/E", pe_str)

        with f2:
            fpe_str = f"{forward_pe:.1f}x" if isinstance(forward_pe, (int, float)) else str(forward_pe)
            metric_card("Forward P/E", fpe_str)

        with f3:
            if fifty_two_week_low != "N/A" and fifty_two_week_high != "N/A":
                metric_card("52W Range", f"${fifty_two_week_low:.2f} – ${fifty_two_week_high:.2f}")
            else:
                metric_card("52W Range", "N/A")

        st.divider()

        # --- Fetch news early (needed for AI memo prompt) -----------------
        news      = stock.news
        news_text = ""

        for article in (news or [])[:5]:
            content = article.get("content", {})
            title   = content.get("title",   "No title")
            summary = content.get("summary", "No summary available")
            news_text += f"Title: {title}\nSummary: {summary}\n\n"

        # --- AI Investment Memo -------------------------------------------
        prompt = f"""
        You are an investment research analyst.

        Analyze the company below using only the provided market data and recent news.
        Do not give direct financial advice. Do not tell the user to buy, sell, or hold.
        Write in a professional but beginner-friendly tone.

        Company: {company_name}
        Ticker: {ticker}
        Sector: {sector}
        Current Price: {current_price}
        Market Cap: {market_cap}
        Selected Time Period: {period_labels[period]}
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

        st.subheader("AI Investment Memo")

        with st.expander("View news text being analyzed"):
            st.write(news_text)

        if st.button("Generate Investment Memo", type="primary"):
            with st.spinner("Analyzing recent news..."):
                response = client.responses.create(
                    model="gpt-5-mini",
                    input=prompt
                )
                render_styled_memo(response.output_text)

        st.divider()

        # --- Period performance -------------------------------------------
        st.markdown(f"##### Within {period_labels[period]}")

        m1, m2, m3 = st.columns(3)
        with m1:
            metric_card("Highest Close", f"${highest_close:,.2f}")
        with m2:
            metric_card("Lowest Close",  f"${lowest_close:,.2f}")
        with m3:
            metric_card("Average Close", f"${avg_close:,.2f}")

        st.divider()

        # --- Price history chart ------------------------------------------
        st.subheader("Price History")
        chart_data = history.reset_index()
        st.altair_chart(green_line_chart(chart_data), use_container_width=True)

        # --- Recent news --------------------------------------------------
        st.divider()
        st.subheader("Recent News")

        if not news:
            st.write("No recent news found.")
        else:
            for article in news[:5]:
                content  = article.get("content", {})
                title    = content.get("title",        "No title")
                summary  = content.get("summary",      "No summary available")
                pub_date = content.get("pubDate",      "No date available")
                url      = content.get("canonicalUrl", {}).get("url", "") or ""
                news_card(title, pub_date, summary, url)

        # --- Comparison section -------------------------------------------
        if ticker2:
            ticker2  = ticker2.upper().strip()
            stock2   = yf.Ticker(ticker2)
            history2 = stock2.history(period=period)

            if history2.empty:
                st.error(f"Comparison ticker '{ticker2}' is invalid.")
            else:
                info2 = stock2.info

                current_price2 = info2.get("currentPrice", "N/A")
                market_cap2    = info2.get("marketCap",    "N/A")
                avg_close2     = history2["Close"].mean()

                st.divider()
                st.subheader(f"Comparison: {ticker} vs {ticker2}")

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown(f"### {ticker}")
                    st.write(company_name)
                    if current_price != "N/A":
                        st.metric("Current Price", f"${current_price:,.2f}")
                    if market_cap != "N/A":
                        st.metric("Market Cap", f"${market_cap:,.0f}")
                    st.metric("Average Close", f"${avg_close:,.2f}")

                with c2:
                    st.markdown(f"### {ticker2}")
                    st.write(info2.get("longName", ticker2))
                    if current_price2 != "N/A":
                        st.metric("Current Price", f"${current_price2:,.2f}")
                    if market_cap2 != "N/A":
                        st.metric("Market Cap", f"${market_cap2:,.0f}")
                    st.metric("Average Close", f"${avg_close2:,.2f}")

                st.subheader(f"{ticker2} Price History")
                chart_data2 = history2.reset_index()
                st.altair_chart(green_line_chart(chart_data2), use_container_width=True)

else:
    st.markdown("""
    <style>
    .metric-card  { border:1px solid rgba(128,128,128,0.2); border-radius:8px; padding:20px 24px; }
    .metric-label { font-size:0.875rem; opacity:0.65; margin:0 0 6px 0; font-weight:500; }
    .positive     { color:#22C55E; margin:4px 0; }
    .negative     { color:#EF4444; margin:4px 0; }
    .muted        { font-size:0.85rem; opacity:0.55; margin:4px 0; }
    .memo-card    { border:1px solid rgba(128,128,128,0.2); border-radius:8px; padding:20px 24px;
                    background:rgba(255,255,255,0.02); }
    .green-card   { border-color:#22C55E; border-left:4px solid #22C55E; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("# 📈 Thesis")
    st.markdown("### Institutional-quality research for everyday investors")
    st.write(
        "Analyze stocks using market performance, fundamental metrics, recent news, "
        "and AI-generated investment memos."
    )

    if st.button("Analyze Your Own Stock", type="primary"):
        msg = st.empty()
        msg.info("Open the sidebar on the left and enter a stock ticker to begin.")
        time.sleep(3)
        msg.empty()

    st.divider()

    st.subheader("Market Snapshot")

    s1, s2, s3 = st.columns(3)

    with s1:
        st.markdown("""
        <div class="metric-card">
            <p class="metric-label">S&amp;P 500</p>
            <h2 class="positive">▲ 0.8%</h2>
            <p class="muted">Broad market strength</p>
        </div>
        """, unsafe_allow_html=True)

    with s2:
        st.markdown("""
        <div class="metric-card">
            <p class="metric-label">NASDAQ</p>
            <h2 class="positive">▲ 1.2%</h2>
            <p class="muted">Tech-led gains</p>
        </div>
        """, unsafe_allow_html=True)

    with s3:
        st.markdown("""
        <div class="metric-card">
            <p class="metric-label">DOW</p>
            <h2 class="negative">▼ 0.3%</h2>
            <p class="muted">Mixed blue-chip performance</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Featured Research Example")

    st.markdown("""
    <div class="memo-card green-card">
        <h4>NVDA · AI Infrastructure</h4>
        <p class="muted">Sample investment memo preview</p>
        <p>
        Nvidia continues to benefit from strong AI infrastructure demand,
        data center expansion, and high-margin accelerator sales. Key risks
        include valuation pressure, supply constraints, and customer concentration.
        </p>
        <p class="positive"><strong>Sample Sentiment: Bullish</strong></p>
    </div>
    """, unsafe_allow_html=True)
