import os
import sys

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

# logic.py lives in the parent folder (next to app.py); make it importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_history(closes):
    """Build a minimal yfinance-style history DataFrame."""
    dates = pd.date_range(start="2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"Close": closes}, index=dates)


def make_mock_stock(closes, info_dict, news_list=None):
    mock = MagicMock()
    mock.history.return_value = make_history(closes)
    mock.info = info_dict
    mock.news = news_list or []
    return mock


# ---------------------------------------------------------------------------
# clean_ticker
# ---------------------------------------------------------------------------

class TestCleanTicker:
    def test_lowercase_becomes_uppercase(self):
        assert logic.clean_ticker("aapl") == "AAPL"

    def test_leading_trailing_spaces_removed(self):
        assert logic.clean_ticker("  AAPL  ") == "AAPL"

    def test_mixed_case_and_spaces(self):
        assert logic.clean_ticker(" msft ") == "MSFT"

    def test_already_clean_unchanged(self):
        assert logic.clean_ticker("TSLA") == "TSLA"

    def test_empty_string(self):
        assert logic.clean_ticker("") == ""

    def test_none_returns_empty(self):
        assert logic.clean_ticker(None) == ""


# ---------------------------------------------------------------------------
# is_valid_history
# ---------------------------------------------------------------------------

class TestHistoryValidation:
    def test_empty_dataframe_is_invalid(self):
        assert logic.is_valid_history(pd.DataFrame()) is False

    def test_non_empty_history_is_valid(self):
        assert logic.is_valid_history(make_history([150.0, 151.0])) is True

    def test_single_row_is_valid(self):
        assert logic.is_valid_history(make_history([200.0])) is True

    def test_none_is_invalid(self):
        assert logic.is_valid_history(None) is False


# ---------------------------------------------------------------------------
# price_stats
# ---------------------------------------------------------------------------

class TestPriceStats:
    def setup_method(self):
        self.stats = logic.price_stats(make_history([100.0, 120.0, 80.0, 110.0, 90.0]))

    def test_highest_close(self):
        assert self.stats["highest"] == 120.0

    def test_lowest_close(self):
        assert self.stats["lowest"] == 80.0

    def test_average_close(self):
        assert self.stats["average"] == pytest.approx(100.0)

    def test_single_price_all_stats_equal(self):
        s = logic.price_stats(make_history([200.0]))
        assert s["highest"] == 200.0
        assert s["lowest"] == 200.0
        assert s["average"] == pytest.approx(200.0)

    def test_identical_prices(self):
        s = logic.price_stats(make_history([150.0, 150.0, 150.0]))
        assert s["highest"] == 150.0
        assert s["lowest"] == 150.0
        assert s["average"] == pytest.approx(150.0)

    def test_float_precision(self):
        s = logic.price_stats(make_history([1.1, 2.2, 3.3]))
        assert s["average"] == pytest.approx(2.2, rel=1e-6)


# ---------------------------------------------------------------------------
# period_label
# ---------------------------------------------------------------------------

class TestPeriodLabel:
    @pytest.mark.parametrize("code,label", [
        ("1mo", "the Last Month"),
        ("3mo", "the Last 3 Months"),
        ("6mo", "the Last 6 Months"),
        ("1y", "the Last Year"),
    ])
    def test_known_periods(self, code, label):
        assert logic.period_label(code) == label

    def test_unknown_period_falls_back_to_code(self):
        assert logic.period_label("5y") == "5y"


# ---------------------------------------------------------------------------
# extract_info
# ---------------------------------------------------------------------------

class TestExtractInfo:
    def test_all_fields_present(self):
        info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "currentPrice": 195.50,
            "marketCap": 3_000_000_000_000,
            "trailingPE": 30.0,
            "forwardPE": 28.0,
            "fiftyTwoWeekHigh": 200.0,
            "fiftyTwoWeekLow": 120.0,
            "profitMargins": 0.25,
            "revenueGrowth": 0.08,
        }
        data = logic.extract_info(info)
        assert data["company_name"] == "Apple Inc."
        assert data["sector"] == "Technology"
        assert data["current_price"] == 195.50
        assert data["market_cap"] == 3_000_000_000_000
        assert data["trailing_pe"] == 30.0
        assert data["forward_pe"] == 28.0
        assert data["fifty_two_week_high"] == 200.0
        assert data["fifty_two_week_low"] == 120.0
        assert data["profit_margins"] == 0.25
        assert data["revenue_growth"] == 0.08

    def test_missing_fields_default_to_na(self):
        data = logic.extract_info({})
        assert data["company_name"] == "N/A"
        assert data["sector"] == "N/A"
        assert data["current_price"] == "N/A"
        assert data["market_cap"] == "N/A"
        assert data["trailing_pe"] == "N/A"
        assert data["forward_pe"] == "N/A"
        assert data["fifty_two_week_high"] == "N/A"
        assert data["fifty_two_week_low"] == "N/A"
        assert data["profit_margins"] == "N/A"
        assert data["revenue_growth"] == "N/A"

    def test_none_info_treated_as_empty(self):
        assert logic.extract_info(None)["company_name"] == "N/A"

    def test_ticker_fallback_for_long_name(self):
        # Mirrors the comparison section: info2.get("longName", ticker2)
        data = logic.extract_info({}, ticker_fallback="MSFT")
        assert data["company_name"] == "MSFT"

    def test_present_long_name_overrides_ticker_fallback(self):
        data = logic.extract_info({"longName": "Microsoft Corporation"}, ticker_fallback="MSFT")
        assert data["company_name"] == "Microsoft Corporation"


# ---------------------------------------------------------------------------
# build_fundamentals_text
# ---------------------------------------------------------------------------

class TestBuildFundamentalsText:
    def test_contains_each_metric(self):
        data = logic.extract_info({
            "trailingPE": 30.0,
            "forwardPE": 28.0,
            "fiftyTwoWeekHigh": 200.0,
            "fiftyTwoWeekLow": 120.0,
            "profitMargins": 0.25,
            "revenueGrowth": 0.08,
        })
        text = logic.build_fundamentals_text(data)
        assert "Trailing P/E: 30.0" in text
        assert "Forward P/E: 28.0" in text
        assert "52-Week High: 200.0" in text
        assert "52-Week Low: 120.0" in text
        assert "Profit Margins: 0.25" in text
        assert "Revenue Growth: 0.08" in text

    def test_na_values_passed_through(self):
        text = logic.build_fundamentals_text(logic.extract_info({}))
        assert "Trailing P/E: N/A" in text


# ---------------------------------------------------------------------------
# News processing
# ---------------------------------------------------------------------------

class TestParseNewsItems:
    def test_well_formed_article(self):
        news = [{
            "content": {
                "title": "Apple hits record high",
                "summary": "Apple stock reached an all-time high today.",
                "pubDate": "2024-06-01T12:00:00Z",
                "canonicalUrl": {"url": "https://example.com/a"},
            }
        }]
        item = logic.parse_news_items(news)[0]
        assert item["title"] == "Apple hits record high"
        assert "all-time high" in item["summary"]
        assert item["pub_date"] == "2024-06-01T12:00:00Z"
        assert item["url"] == "https://example.com/a"

    def test_missing_fields_fall_back(self):
        item = logic.parse_news_items([{}])[0]
        assert item["title"] == "No title"
        assert item["summary"] == "No summary available"
        assert item["pub_date"] == "No date available"
        assert item["url"] == ""

    def test_missing_canonical_url_is_empty_string(self):
        item = logic.parse_news_items([{"content": {"title": "x"}}])[0]
        assert item["url"] == ""

    def test_none_canonical_url_is_empty_string(self):
        item = logic.parse_news_items([{"content": {"canonicalUrl": None}}])[0]
        assert item["url"] == ""

    def test_empty_and_none_news(self):
        assert logic.parse_news_items([]) == []
        assert logic.parse_news_items(None) == []

    def test_sliced_to_five(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(10)]
        items = logic.parse_news_items(news)
        assert len(items) == 5
        assert items[-1]["title"] == "Article 4"

    def test_fewer_than_five_not_padded(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(3)]
        assert len(logic.parse_news_items(news)) == 3

    def test_custom_limit(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(10)]
        assert len(logic.parse_news_items(news, limit=2)) == 2


class TestBuildNewsText:
    def test_includes_titles_and_summaries(self):
        news = [
            {"content": {"title": "Big news", "summary": "Details."}},
            {"content": {"title": "More news", "summary": "More details."}},
        ]
        text = logic.build_news_text(news)
        assert "Title: Big news" in text
        assert "Summary: Details." in text
        assert "Title: More news" in text

    def test_empty_news_is_empty_string(self):
        assert logic.build_news_text([]) == ""
        assert logic.build_news_text(None) == ""

    def test_missing_fields_fall_back(self):
        text = logic.build_news_text([{}])
        assert "Title: No title" in text
        assert "Summary: No summary available" in text

    def test_sliced_to_five(self):
        news = [{"content": {"title": f"A{i}", "summary": "s"}} for i in range(10)]
        text = logic.build_news_text(news)
        assert text.count("Title:") == 5


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_format_price(self):
        assert logic.format_price(1234.5) == "$1,234.50"
        assert logic.format_price(195.5) == "$195.50"

    def test_format_price_na(self):
        assert logic.format_price("N/A") == "N/A"
        assert logic.format_price(None) == "N/A"

    def test_format_market_cap_trillions(self):
        assert logic.format_market_cap_trillions(2_400_000_000_000) == "$2.40T"

    def test_format_market_cap_trillions_na(self):
        assert logic.format_market_cap_trillions("N/A") == "N/A"

    def test_format_pe_numeric(self):
        assert logic.format_pe(30.04) == "30.0x"
        assert logic.format_pe(28) == "28.0x"

    def test_format_pe_non_numeric(self):
        assert logic.format_pe("N/A") == "N/A"

    def test_format_percent_signed_positive(self):
        text, positive = logic.format_percent_signed(0.082)
        assert text == "8.2%"
        assert positive is True

    def test_format_percent_signed_negative(self):
        text, positive = logic.format_percent_signed(-0.05)
        assert text == "5.0%"
        assert positive is False

    def test_format_percent_signed_zero_is_positive(self):
        text, positive = logic.format_percent_signed(0.0)
        assert text == "0.0%"
        assert positive is True

    def test_format_percent_signed_na(self):
        assert logic.format_percent_signed("N/A") == (None, None)
        assert logic.format_percent_signed(None) == (None, None)

    def test_format_52w_range(self):
        assert logic.format_52w_range(120.0, 200.0) == "$120.00 – $200.00"

    def test_format_52w_range_na(self):
        assert logic.format_52w_range("N/A", 200.0) == "N/A"
        assert logic.format_52w_range(120.0, "N/A") == "N/A"


# ---------------------------------------------------------------------------
# build_memo_prompt
# ---------------------------------------------------------------------------

class TestBuildMemoPrompt:
    def _prompt(self):
        return logic.build_memo_prompt(
            company_name="Apple Inc.",
            ticker="AAPL",
            sector="Technology",
            current_price=195.5,
            market_cap=3_000_000_000_000,
            period="1mo",
            highest_close=200.0,
            lowest_close=180.0,
            avg_close=190.0,
            fundamentals_text="Trailing P/E: 30.0",
            news_text="Title: Big news\nSummary: Details.",
        )

    def test_includes_company_and_ticker(self):
        prompt = self._prompt()
        assert "Company: Apple Inc." in prompt
        assert "Ticker: AAPL" in prompt

    def test_uses_human_friendly_period_label(self):
        assert "Selected Time Period: the Last Month" in self._prompt()

    def test_embeds_fundamentals_and_news(self):
        prompt = self._prompt()
        assert "Trailing P/E: 30.0" in prompt
        assert "Title: Big news" in prompt

    def test_contains_all_section_headers(self):
        prompt = self._prompt()
        for header in logic.SECTION_COLORS:
            assert f"### {header}" in prompt

    def test_includes_guardrails(self):
        prompt = self._prompt()
        assert "Do not provide a buy, sell, or hold recommendation." in prompt
        assert "Never use dollar signs" in prompt


# ---------------------------------------------------------------------------
# generate_memo (OpenAI client mocked)
# ---------------------------------------------------------------------------

class TestGenerateMemo:
    def test_calls_client_and_returns_text(self):
        client = MagicMock()
        client.responses.create.return_value = MagicMock(output_text="### Conclusion\nGood.")
        result = logic.generate_memo(client, "PROMPT")
        assert result == "### Conclusion\nGood."
        client.responses.create.assert_called_once_with(model="gpt-5-mini", input="PROMPT")

    def test_respects_custom_model(self):
        client = MagicMock()
        client.responses.create.return_value = MagicMock(output_text="ok")
        logic.generate_memo(client, "PROMPT", model="gpt-4o")
        client.responses.create.assert_called_once_with(model="gpt-4o", input="PROMPT")


# ---------------------------------------------------------------------------
# md_to_html
# ---------------------------------------------------------------------------

class TestMdToHtml:
    def test_paragraph(self):
        html = logic.md_to_html("Hello world.")
        assert "<p" in html and "Hello world." in html

    def test_bullet_list(self):
        html = logic.md_to_html("- one\n- two")
        assert "<ul" in html
        assert html.count("<li") == 2
        assert "</ul>" in html

    def test_numbered_list(self):
        html = logic.md_to_html("1. first\n2. second")
        assert "<ol" in html
        assert html.count("<li") == 2
        assert "</ol>" in html

    def test_bold_conversion(self):
        html = logic.md_to_html("This is **bold** text.")
        assert "<strong>bold</strong>" in html

    def test_html_is_escaped(self):
        html = logic.md_to_html("5 < 10 & rising")
        assert "&lt;" in html
        assert "&amp;" in html

    def test_switch_from_ul_to_ol_closes_ul(self):
        html = logic.md_to_html("- bullet\n1. number")
        assert "</ul>" in html
        assert "<ol" in html


# ---------------------------------------------------------------------------
# parse_memo_sections
# ---------------------------------------------------------------------------

class TestParseMemoSections:
    SAMPLE = (
        "### Executive Summary\n"
        "A short overview.\n\n"
        "### Risk Factors\n"
        "- Risk one\n- Risk two\n\n"
        "### Mystery Section\n"
        "Unknown header body."
    )

    def test_splits_into_sections(self):
        sections = logic.parse_memo_sections(self.SAMPLE)
        headers = [s["header"] for s in sections]
        assert headers == ["Executive Summary", "Risk Factors", "Mystery Section"]

    def test_captures_body(self):
        sections = logic.parse_memo_sections(self.SAMPLE)
        assert sections[0]["body"] == "A short overview."
        assert "Risk one" in sections[1]["body"]

    def test_known_header_gets_mapped_color(self):
        sections = logic.parse_memo_sections(self.SAMPLE)
        assert sections[0]["color"] == logic.SECTION_COLORS["Executive Summary"]

    def test_unknown_header_gets_default_color(self):
        sections = logic.parse_memo_sections(self.SAMPLE)
        assert sections[-1]["color"] == logic.DEFAULT_SECTION_COLOR

    def test_header_without_body(self):
        sections = logic.parse_memo_sections("### Conclusion")
        assert sections[0]["header"] == "Conclusion"
        assert sections[0]["body"] == ""

    def test_empty_analysis_yields_no_sections(self):
        assert logic.parse_memo_sections("") == []


# ---------------------------------------------------------------------------
# yfinance integration (mocked) — end-to-end through logic helpers
# ---------------------------------------------------------------------------

class TestYFinanceIntegration:

    @patch("yfinance.Ticker")
    def test_valid_ticker_history_not_empty(self, mock_cls):
        mock_cls.return_value = make_mock_stock(
            [150.0, 155.0, 148.0],
            {"longName": "Apple Inc.", "currentPrice": 155.0, "marketCap": 2_400_000_000_000},
        )
        import yfinance as yf
        stock = yf.Ticker("AAPL")
        assert logic.is_valid_history(stock.history(period="1mo"))

    @patch("yfinance.Ticker")
    def test_invalid_ticker_returns_empty_history(self, mock_cls):
        mock = MagicMock()
        mock.history.return_value = pd.DataFrame()
        mock_cls.return_value = mock
        import yfinance as yf
        stock = yf.Ticker("FAKEXYZ")
        assert logic.is_valid_history(stock.history(period="1mo")) is False

    @patch("yfinance.Ticker")
    def test_price_stats_computed_from_history(self, mock_cls):
        mock_cls.return_value = make_mock_stock([100.0, 200.0, 150.0], {"longName": "Test Corp"})
        import yfinance as yf
        stats = logic.price_stats(yf.Ticker("TEST").history(period="1mo"))
        assert stats["highest"] == 200.0
        assert stats["lowest"] == 100.0
        assert stats["average"] == pytest.approx(150.0)

    @patch("yfinance.Ticker")
    def test_news_parsed_from_stock(self, mock_cls):
        news = [
            {"content": {"title": "Big news", "summary": "Details.", "pubDate": "2024-01-01"}},
            {"content": {"title": "More news", "summary": "More details.", "pubDate": "2024-01-02"}},
        ]
        mock_cls.return_value = make_mock_stock([100.0], {"longName": "Apple Inc."}, news_list=news)
        import yfinance as yf
        items = logic.parse_news_items(yf.Ticker("AAPL").news)
        assert len(items) == 2
        assert items[0]["title"] == "Big news"

    @patch("yfinance.Ticker")
    def test_no_news_returns_empty_list(self, mock_cls):
        mock_cls.return_value = make_mock_stock([100.0], {"longName": "Apple Inc."}, news_list=[])
        import yfinance as yf
        assert logic.parse_news_items(yf.Ticker("AAPL").news) == []

    @patch("yfinance.Ticker")
    def test_both_tickers_valid(self, mock_cls):
        def side_effect(sym):
            if sym == "AAPL":
                return make_mock_stock(
                    [150.0, 155.0],
                    {"longName": "Apple Inc.", "currentPrice": 155.0, "marketCap": 2_000_000_000_000},
                )
            return make_mock_stock(
                [400.0, 420.0],
                {"longName": "Microsoft Corporation", "currentPrice": 420.0, "marketCap": 3_000_000_000_000},
            )
        mock_cls.side_effect = side_effect
        import yfinance as yf
        s1, s2 = yf.Ticker("AAPL"), yf.Ticker("MSFT")
        assert logic.is_valid_history(s1.history(period="1mo"))
        assert logic.is_valid_history(s2.history(period="1mo"))
        assert logic.extract_info(s1.info)["company_name"] == "Apple Inc."
        assert logic.extract_info(s2.info)["company_name"] == "Microsoft Corporation"

    @patch("yfinance.Ticker")
    def test_primary_valid_comparison_invalid(self, mock_cls):
        def side_effect(sym):
            if sym == "AAPL":
                return make_mock_stock([150.0], {"longName": "Apple Inc.", "currentPrice": 150.0})
            mock = MagicMock()
            mock.history.return_value = pd.DataFrame()
            return mock
        mock_cls.side_effect = side_effect
        import yfinance as yf
        s1, s2 = yf.Ticker("AAPL"), yf.Ticker("BADTICKER")
        assert logic.is_valid_history(s1.history(period="1mo"))
        assert logic.is_valid_history(s2.history(period="1mo")) is False

    @patch("yfinance.Ticker")
    def test_info_na_fields_when_data_missing(self, mock_cls):
        mock_cls.return_value = make_mock_stock([100.0], {})
        import yfinance as yf
        data = logic.extract_info(yf.Ticker("SPARSE").info)
        assert data["current_price"] == "N/A"
        assert data["market_cap"] == "N/A"
        assert data["company_name"] == "N/A"
        assert data["sector"] == "N/A"
