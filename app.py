import html
import streamlit as st
import yfinance as yf
import altair as alt
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from dotenv import load_dotenv
import os

import logic

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

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


def green_line_chart(df, period="1mo", height=300):
    if period in ("1mo", "3mo"):
        fmt, ticks = "%b %d", "week"
    else:
        fmt, ticks = "%b %Y", "month"

    return (
        alt.Chart(df)
        .mark_line(color="#22C55E", strokeWidth=2)
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(title="", format=fmt, tickCount=ticks, labelAngle=-30)),
            y=alt.Y("Close:Q", axis=alt.Axis(title="Closing Price (USD)"), scale=alt.Scale(zero=False)),
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_info(ticker):
    return yf.Ticker(ticker).info


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)


@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_news(ticker):
    try:
        return yf.Ticker(ticker).news
    except Exception:
        return []


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
        <div style="border:1px solid rgba(128,128,128,0.25);border-left:3px solid #22C55E;
                    border-radius:8px;padding:20px 24px;margin-bottom:12px;">
            <div style="font-weight:600;font-size:1rem;margin-bottom:6px;line-height:1.4;">{safe_title}</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.45);margin-bottom:12px;">{safe_date}</div>
            <div style="font-size:0.9rem;color:rgba(255,255,255,0.8);line-height:1.5;
                        margin-bottom:{bottom_margin};">{safe_summary}</div>
            {link_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def generate_and_render_memo(prompt, spinner_text):
    """Generate and display an AI memo with user-friendly error handling."""
    if client is None:
        st.error(
            "AI analysis is unavailable because no OpenAI API key was found. "
            "Add OPENAI_API_KEY to your .env file and restart the app."
        )
        return

    try:
        with st.spinner(spinner_text):
            memo = logic.generate_memo(client, prompt)
        render_styled_memo(memo)

    except RateLimitError:
        st.error("The AI service is temporarily rate-limited. Please wait a moment and try again.")
    except APIConnectionError:
        st.error("Could not connect to the AI service. Check your internet connection and try again.")
    except APIStatusError:
        st.error("The AI service returned an error. Please try again shortly.")
    except Exception:
        st.error("Something unexpected happened while generating the memo. Please try again.")


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
    st.markdown(
        '<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;'
        'color:rgba(255,255,255,0.4);text-transform:uppercase;margin-bottom:10px;">Stock Lookup</div>',
        unsafe_allow_html=True,
    )
    ticker  = st.text_input("Primary ticker", placeholder="e.g. AAPL", key="ticker_input")
    ticker2 = st.text_input("Comparison ticker", placeholder="e.g. MSFT (optional)")

    st.markdown(
        '<div style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;'
        'color:rgba(255,255,255,0.4);text-transform:uppercase;margin:14px 0 10px 0;">Time Range</div>',
        unsafe_allow_html=True,
    )
    period = st.selectbox(
        "Time Range",
        ["1mo", "3mo", "6mo", "1y"],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("Thesis generates AI-powered investment research using market data, fundamentals, and recent news.")
    st.markdown(
        '<div style="font-size:0.72rem;color:rgba(255,255,255,0.3);line-height:1.5;margin-top:8px;">'
        '⚠︎ For informational purposes only. Nothing on this platform constitutes financial advice. '
        'Always do your own research before making investment decisions.'
        '</div>',
        unsafe_allow_html=True,
    )


if ticker:
    ticker = logic.clean_ticker(ticker)

    try:
        history  = get_stock_history(ticker, period)
        raw_info = get_stock_info(ticker)
    except Exception:
        st.error("Market data is temporarily unavailable due to rate limiting. Please try again in a moment.")
        st.stop()

    if not logic.is_valid_history(history):
        st.error("Invalid ticker. Please double-check the symbol and try again.")
    else:
        data = logic.extract_info(raw_info)

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
        news      = get_stock_news(ticker)
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

        with st.expander("Sources used in this analysis"):
            st.write(news_text)

        if st.button("Generate Investment Memo", type="primary"):
            generate_and_render_memo(
                prompt,
                "Analyzing recent news...",
            )

        st.divider()

        # --- Period performance -------------------------------------------
        st.subheader(f"Within {logic.period_label(period)}")

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
        st.altair_chart(green_line_chart(chart_data, period=period), use_container_width=True)

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
            ticker2 = logic.clean_ticker(ticker2)

            try:
                history2  = get_stock_history(ticker2, period)
                raw_info2 = get_stock_info(ticker2)
            except Exception:
                st.error(f"Market data for '{ticker2}' is temporarily unavailable. Please try again in a moment.")
                history2  = None
                raw_info2 = {}

            if not logic.is_valid_history(history2):
                st.error(f"Comparison ticker '{ticker2}' is invalid.")
            else:
                data2 = logic.extract_info(raw_info2, ticker_fallback=ticker2)

                fundamentals_text2 = logic.build_fundamentals_text(data2)

                news2 = get_stock_news(ticker2)

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
                    st.markdown(
                        f'<div style="font-size:1.1rem;font-weight:700;margin-bottom:4px;">{ticker}</div>'
                        f'<div style="font-size:0.85rem;color:rgba(255,255,255,0.5);margin-bottom:14px;">{company_name}</div>',
                        unsafe_allow_html=True,
                    )
                    metric_card("Current Price", logic.format_price(current_price))
                    metric_card("Market Cap", logic.format_market_cap_trillions(market_cap))
                    metric_card("Average Close", logic.format_price(avg_close))

                with c2:
                    st.markdown(
                        f'<div style="font-size:1.1rem;font-weight:700;margin-bottom:4px;">{ticker2}</div>'
                        f'<div style="font-size:0.85rem;color:rgba(255,255,255,0.5);margin-bottom:14px;">{data2["company_name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    metric_card("Current Price", logic.format_price(current_price2))
                    metric_card("Market Cap", logic.format_market_cap_trillions(market_cap2))
                    metric_card("Average Close", logic.format_price(avg_close2))

                st.subheader("AI Comparison Memo")

                if st.button("Generate AI Comparison Memo", type="primary"):
                    generate_and_render_memo(
                        comparison_prompt,
                        f"Comparing {ticker} and {ticker2}...",
                    )

                st.divider()

                st.subheader(f"{ticker2} Price History")
                chart_data2 = history2.reset_index()
                st.altair_chart(green_line_chart(chart_data2, period=period), use_container_width=True)

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

    if "show_ticker_hint" not in st.session_state:
        st.session_state["show_ticker_hint"] = False

    if st.button("Analyze Your Own Stock", type="primary"):
        st.session_state["show_ticker_hint"] = True

    if st.session_state["show_ticker_hint"]:
        st.info("Enter a stock ticker in the sidebar to begin.")

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
