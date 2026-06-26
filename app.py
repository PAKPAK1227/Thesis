import html
import time
import streamlit as st
import yfinance as yf
import altair as alt
from openai import OpenAI
from dotenv import load_dotenv
import os

import logic

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


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_snapshot():
    """Fetch recent history for the major U.S. market indexes."""
    histories = {}

    for symbol in logic.MARKET_INDEXES.values():
        try:
            histories[symbol] = yf.Ticker(symbol).history(period="5d")
        except Exception:
            histories[symbol] = None

    return logic.market_snapshot_from_histories(histories)


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


def render_styled_memo(analysis: str):
    """Parse the AI memo and render each section as a color-coded card."""
    for section in logic.parse_memo_sections(analysis):
        header = section["header"]
        color  = section["color"]
        body_html = logic.md_to_html(section["body"]) if section["body"] else ""

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


# Clear ticker before any widget is instantiated
if st.session_state.get("_clear_ticker"):
    del st.session_state["_clear_ticker"]
    st.session_state["ticker_input"] = ""

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
    ticker  = st.text_input("Stock ticker", placeholder="e.g. AAPL", key="ticker_input")
    ticker2 = st.text_input("Comparison ticker optional", placeholder="e.g. MSFT")

    period = st.selectbox(
        "Time Range",
        ["1mo", "3mo", "6mo", "1y"],
    )

    st.caption("Thesis generates AI-powered investment research using market data, fundamentals, and recent news.")


if ticker:
    ticker  = logic.clean_ticker(ticker)
    stock   = yf.Ticker(ticker)
    history = stock.history(period=period)

    if not logic.is_valid_history(history):
        st.error("Invalid ticker. Please double-check the symbol and try again.")
    else:
        data = logic.extract_info(stock.info)

        company_name        = data["company_name"]
        sector              = data["sector"]
        current_price       = data["current_price"]
        market_cap          = data["market_cap"]
        trailing_pe         = data["trailing_pe"]
        forward_pe          = data["forward_pe"]
        fifty_two_week_high = data["fifty_two_week_high"]
        fifty_two_week_low  = data["fifty_two_week_low"]
        profit_margins      = data["profit_margins"]
        revenue_growth      = data["revenue_growth"]

        stats = logic.price_stats(history)
        highest_close = stats["highest"]
        lowest_close  = stats["lowest"]
        avg_close     = stats["average"]

        fundamentals_text = logic.build_fundamentals_text(data)

        # --- Back button --------------------------------------------------
        if st.button("← Back to Home"):
            st.session_state["_clear_ticker"] = True
            st.rerun()

        # --- Company header -----------------------------------------------
        st.title(f"{company_name} ({ticker})")
        st.caption(f"Sector: {sector}")

        # --- KPI cards ----------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("Price", logic.format_price(current_price))

        with c2:
            metric_card("Market Cap", logic.format_market_cap_trillions(market_cap))

        with c3:
            rg_text, rg_positive = logic.format_percent_signed(revenue_growth)
            metric_card("Revenue Growth", rg_text or "N/A", positive=rg_positive)

        with c4:
            pm_text, pm_positive = logic.format_percent_signed(profit_margins)
            metric_card("Profit Margin", pm_text or "N/A", positive=pm_positive)

        st.divider()

        # --- Financial Snapshot -------------------------------------------
        st.subheader("Financial Snapshot")

        f1, f2, f3 = st.columns(3)

        with f1:
            metric_card("Trailing P/E", logic.format_pe(trailing_pe))

        with f2:
            metric_card("Forward P/E", logic.format_pe(forward_pe))

        with f3:
            metric_card("52W Range", logic.format_52w_range(fifty_two_week_low, fifty_two_week_high))

        st.divider()

        # --- Fetch news early (needed for AI memo prompt) -----------------
        news      = stock.news
        news_text = logic.build_news_text(news)

        # --- AI Investment Memo -------------------------------------------
        prompt = logic.build_memo_prompt(
            company_name=company_name,
            ticker=ticker,
            sector=sector,
            current_price=current_price,
            market_cap=market_cap,
            period=period,
            highest_close=highest_close,
            lowest_close=lowest_close,
            avg_close=avg_close,
            fundamentals_text=fundamentals_text,
            news_text=news_text,
        )

        st.subheader("AI Investment Memo")

        with st.expander("View news text being analyzed"):
            st.write(news_text)

        if st.button("Generate Investment Memo", type="primary"):
            with st.spinner("Analyzing recent news..."):
                memo = logic.generate_memo(client, prompt)
                render_styled_memo(memo)

        st.divider()

        # --- Period performance -------------------------------------------
        st.markdown(f"##### Within {logic.period_label(period)}")

        m1, m2, m3 = st.columns(3)
        with m1:
            metric_card("Highest Close", logic.format_price(highest_close))
        with m2:
            metric_card("Lowest Close",  logic.format_price(lowest_close))
        with m3:
            metric_card("Average Close", logic.format_price(avg_close))

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
            for item in logic.parse_news_items(news):
                news_card(item["title"], item["pub_date"], item["summary"], item["url"])

        # --- Comparison section -------------------------------------------
        if ticker2:
            ticker2  = logic.clean_ticker(ticker2)
            stock2   = yf.Ticker(ticker2)
            history2 = stock2.history(period=period)

            if not logic.is_valid_history(history2):
                st.error(f"Comparison ticker '{ticker2}' is invalid.")
            else:
                data2 = logic.extract_info(stock2.info, ticker_fallback=ticker2)

                fundamentals_text2 = logic.build_fundamentals_text(data2)

                try:
                    news2 = stock2.news
                except Exception:
                    news2 = []

                news_text2 = logic.build_news_text(news2)

                current_price2 = data2["current_price"]
                market_cap2    = data2["market_cap"]
                avg_close2     = logic.price_stats(history2)["average"]

                comparison_prompt = logic.build_comparison_prompt(
                    company_name1=company_name,
                    ticker1=ticker,
                    sector1=sector,
                    fundamentals_text1=fundamentals_text,
                    news_text1=news_text,
                    average_close1=avg_close,
                    company_name2=data2["company_name"],
                    ticker2=ticker2,
                    sector2=data2["sector"],
                    fundamentals_text2=fundamentals_text2,
                    news_text2=news_text2,
                    average_close2=avg_close2,
                    period=period,
                )

                st.divider()
                st.subheader(f"Comparison: {ticker} vs {ticker2}")

                c1, c2 = st.columns(2)

                with c1:
                    st.markdown(f"### {ticker}")
                    st.write(company_name)
                    if current_price != "N/A":
                        st.metric("Current Price", logic.format_price(current_price))
                    if market_cap != "N/A":
                        st.metric("Market Cap", f"${market_cap:,.0f}")
                    st.metric("Average Close", logic.format_price(avg_close))

                with c2:
                    st.markdown(f"### {ticker2}")
                    st.write(data2["company_name"])
                    if current_price2 != "N/A":
                        st.metric("Current Price", logic.format_price(current_price2))
                    if market_cap2 != "N/A":
                        st.metric("Market Cap", f"${market_cap2:,.0f}")
                    st.metric("Average Close", logic.format_price(avg_close2))

                st.subheader("AI Comparison Memo")

                if st.button("Generate AI Comparison Memo", type="primary"):
                    with st.spinner(f"Comparing {ticker} and {ticker2}..."):
                        comparison_memo = logic.generate_memo(client, comparison_prompt)
                        render_styled_memo(comparison_memo)

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
    st.caption("Latest available market session")

    snapshot = fetch_market_snapshot()
    columns = st.columns(len(snapshot))

    for column, index_data in zip(columns, snapshot):
        with column:
            change_pct = index_data["change_pct"]
            close = index_data["close"]

            if change_pct is None or close is None:
                metric_card(index_data["label"], "Unavailable")
                st.caption("Market data unavailable")
            else:
                direction = (
                    True if change_pct > 0
                    else False if change_pct < 0
                    else None
                )

                metric_card(
                    index_data["label"],
                    f"{abs(change_pct):.2f}%",
                    positive=direction,
                )
                st.caption(f"Latest close: {logic.format_price(close)}")

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
