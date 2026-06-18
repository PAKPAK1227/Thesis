import streamlit as st
import yfinance as yf
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# --- Page setup -----------------------------------------------------------
st.set_page_config(
    page_title="Thesis",
    page_icon="📈",
    layout="centered",
)

st.title("📈 Thesis")
st.caption("Enter a stock ticker to see a clean, at-a-glance snapshot.")

ticker = st.text_input("Stock ticker", placeholder="e.g. AAPL")
ticker2 = st.text_input("Comparison ticker optional", placeholder = "e.g. MSFT")

period = st.selectbox(
    "Time Range",
    ["1mo", "3mo", "6mo", "1y"],
)

# Human-friendly labels for the selected period
period_labels = {
    "1mo": "the Last Month",
    "3mo": "the Last 3 Months",
    "6mo": "the Last 6 Months",
    "1y": "the Last Year",
}

if ticker:
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)

    if history.empty:
        st.error("Invalid ticker. Please double-check the symbol and try again.")
    else:
        info = stock.info  # dictionary

        company_name = info.get("longName", "N/A")
        sector = info.get("sector", "N/A")
        current_price = info.get("currentPrice", "N/A")
        market_cap = info.get("marketCap", "N/A")

        highest_close = history["Close"].max()
        lowest_close = history["Close"].min()
        avg_close = history["Close"].mean()

        # --- Company header ------------------------------------------------
        st.subheader(company_name)
        st.caption(f"Sector: {sector}")

        st.divider()

        # --- Key metrics ---------------------------------------------------
        col1, col2 = st.columns(2)

        with col1:
            if current_price != "N/A":
                st.metric("Current Price", f"${current_price:,.2f}")
            else:
                st.metric("Current Price", "N/A")

        with col2:
            if market_cap != "N/A":
                st.metric("Market Cap", f"${market_cap:,.0f}")
            else:
                st.metric("Market Cap", "N/A")

        st.divider()

        # --- Period performance --------------------------------------------
        st.markdown(f"##### Within {period_labels[period]}")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Highest Close", f"${highest_close:,.2f}")
        with m2:
            st.metric("Lowest Close", f"${lowest_close:,.2f}")
        with m3:
            st.metric("Average Close", f"${avg_close:,.2f}")

        st.divider()

        # --- Price history chart -------------------------------------------
        st.subheader("Price History")
        chart_data = history.reset_index()
        st.line_chart(chart_data, x="Date", y="Close")

        # --- Recent news --------------------------------------------------
        st.divider()
        st.subheader("Recent News")

        news = stock.news
        news_text = ""

        if not news:
            st.write("No recent news found.")
        else:
            for article in news[:5]:
                content = article.get("content", {})

                title = content.get("title", "No title")
                summary = content.get("summary", "No summary available")
                pub_date = content.get("pubDate", "No date available")

                news_text += f"Title: {title}\nSummary: {summary}\n\n"

                st.markdown(f"**{title}**")
                st.caption(pub_date)
                st.write(summary)
                st.divider()

            st.subheader("AI Analysis Input")

            with st.expander("View news text being analyzed"):
                st.write(news_text)  

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

            Recent News:
            {news_text}

            Provide the output in this exact structure:

            ### Overall Sentiment
            Bullish, Bearish, Neutral, or Mixed. Give a 1-2 sentence explanation.

            ### Key Drivers
            - List 3-5 major themes affecting the company.

            ### Bull Case
            - Explain the strongest positive argument for the stock.

            ### Bear Case
            - Explain the strongest risks or negative argument.

            ### Key Risks to Watch
            - List 3-5 risks investors should monitor.

            ### Analyst-Style Outlook
            Write a concise paragraph summarizing the investment narrative.
            """

            

            st.subheader("AI Investment Brief")

            if st.button("Generate AI Analysis"):
                with st.spinner("Analyzing recent news..."):
                    response = client.responses.create(
                        model="gpt-5-mini",
                        input=prompt
                    )

                    analysis = response.output_text
                    st.markdown(analysis)

        # --- Comparison section --------------------------------------------
        if ticker2:
            ticker2 = ticker2.upper().strip()
            stock2 = yf.Ticker(ticker2)
            history2 = stock2.history(period=period)

            if history2.empty:
                st.error(f"Comparison ticker '{ticker2}' is invalid.")
            else:
                info2 = stock2.info

                current_price2 = info2.get("currentPrice", "N/A")
                market_cap2 = info2.get("marketCap", "N/A")
                avg_close2 = history2["Close"].mean()

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
                st.line_chart(chart_data2, x="Date", y="Close")
