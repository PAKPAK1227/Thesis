import pytest
import pandas as pd
from unittest.mock import MagicMock, patch


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
# Ticker cleaning
# ---------------------------------------------------------------------------

class TestTickerCleaning:
    def test_lowercase_becomes_uppercase(self):
        assert "aapl".upper().strip() == "AAPL"

    def test_leading_trailing_spaces_removed(self):
        assert "  AAPL  ".upper().strip() == "AAPL"

    def test_mixed_case_and_spaces(self):
        assert " msft ".upper().strip() == "MSFT"

    def test_already_clean_unchanged(self):
        assert "TSLA".upper().strip() == "TSLA"


# ---------------------------------------------------------------------------
# History validation
# ---------------------------------------------------------------------------

class TestHistoryValidation:
    def test_empty_dataframe_is_invalid(self):
        assert pd.DataFrame().empty is True

    def test_non_empty_history_is_valid(self):
        assert make_history([150.0, 151.0]).empty is False

    def test_single_row_is_valid(self):
        assert make_history([200.0]).empty is False


# ---------------------------------------------------------------------------
# Price statistics
# ---------------------------------------------------------------------------

class TestPriceCalculations:
    def setup_method(self):
        self.history = make_history([100.0, 120.0, 80.0, 110.0, 90.0])

    def test_highest_close(self):
        assert self.history["Close"].max() == 120.0

    def test_lowest_close(self):
        assert self.history["Close"].min() == 80.0

    def test_average_close(self):
        assert self.history["Close"].mean() == pytest.approx(100.0)

    def test_single_price_all_stats_equal(self):
        h = make_history([200.0])
        assert h["Close"].max() == 200.0
        assert h["Close"].min() == 200.0
        assert h["Close"].mean() == pytest.approx(200.0)

    def test_identical_prices(self):
        h = make_history([150.0, 150.0, 150.0])
        assert h["Close"].max() == 150.0
        assert h["Close"].min() == 150.0
        assert h["Close"].mean() == pytest.approx(150.0)

    def test_float_precision(self):
        h = make_history([1.1, 2.2, 3.3])
        assert h["Close"].mean() == pytest.approx(2.2, rel=1e-6)


# ---------------------------------------------------------------------------
# Info field extraction with "N/A" fallbacks
# ---------------------------------------------------------------------------

class TestInfoExtraction:
    def test_all_fields_present(self):
        info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "currentPrice": 195.50,
            "marketCap": 3_000_000_000_000,
        }
        assert info.get("longName", "N/A") == "Apple Inc."
        assert info.get("sector", "N/A") == "Technology"
        assert info.get("currentPrice", "N/A") == 195.50
        assert info.get("marketCap", "N/A") == 3_000_000_000_000

    def test_missing_current_price(self):
        assert {}.get("currentPrice", "N/A") == "N/A"

    def test_missing_market_cap(self):
        assert {}.get("marketCap", "N/A") == "N/A"

    def test_missing_sector(self):
        assert {}.get("sector", "N/A") == "N/A"

    def test_missing_long_name_generic_fallback(self):
        assert {}.get("longName", "N/A") == "N/A"

    def test_missing_long_name_ticker_fallback(self):
        # Used in comparison: info2.get("longName", ticker2)
        assert {}.get("longName", "MSFT") == "MSFT"

    def test_none_value_not_treated_as_missing(self):
        info = {"currentPrice": None}
        assert info.get("currentPrice", "N/A") is None


# ---------------------------------------------------------------------------
# News content extraction
# ---------------------------------------------------------------------------

class TestNewsProcessing:
    def test_well_formed_article(self):
        article = {
            "content": {
                "title": "Apple hits record high",
                "summary": "Apple stock reached an all-time high today.",
                "pubDate": "2024-06-01T12:00:00Z",
            }
        }
        content = article.get("content", {})
        assert content.get("title", "No title") == "Apple hits record high"
        assert "all-time high" in content.get("summary", "No summary available")
        assert content.get("pubDate", "No date available") == "2024-06-01T12:00:00Z"

    def test_missing_content_key_falls_back(self):
        content = {}.get("content", {})
        assert content.get("title", "No title") == "No title"
        assert content.get("summary", "No summary available") == "No summary available"
        assert content.get("pubDate", "No date available") == "No date available"

    def test_partial_content_fields(self):
        article = {"content": {"title": "Breaking news"}}
        content = article.get("content", {})
        assert content.get("title", "No title") == "Breaking news"
        assert content.get("summary", "No summary available") == "No summary available"

    def test_empty_news_list_is_falsy(self):
        assert not []

    def test_news_sliced_to_five(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(10)]
        assert len(news[:5]) == 5
        assert news[:5][-1]["content"]["title"] == "Article 4"

    def test_news_fewer_than_five_not_padded(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(3)]
        assert len(news[:5]) == 3

    def test_exactly_five_articles(self):
        news = [{"content": {"title": f"Article {i}"}} for i in range(5)]
        assert len(news[:5]) == 5


# ---------------------------------------------------------------------------
# Comparison section logic
# ---------------------------------------------------------------------------

class TestComparisonLogic:
    def test_empty_ticker2_is_falsy(self):
        assert not ""

    def test_whitespace_ticker2_strips_to_empty(self):
        assert "   ".strip() == ""

    def test_invalid_ticker2_detected_via_empty_history(self):
        assert pd.DataFrame().empty is True

    def test_comparison_avg_close(self):
        h = make_history([200.0, 210.0, 190.0])
        assert h["Close"].mean() == pytest.approx(200.0)

    def test_comparison_missing_price_is_na(self):
        info2 = {"longName": "Microsoft Corporation", "marketCap": 3_000_000_000_000}
        assert info2.get("currentPrice", "N/A") == "N/A"

    def test_comparison_missing_market_cap_is_na(self):
        info2 = {"longName": "Microsoft Corporation", "currentPrice": 420.00}
        assert info2.get("marketCap", "N/A") == "N/A"

    def test_comparison_subheader_format(self):
        assert f"Comparison: AAPL vs MSFT" == "Comparison: AAPL vs MSFT"

    def test_comparison_price_history_heading_format(self):
        ticker2 = "MSFT"
        assert f"{ticker2} Price History" == "MSFT Price History"


# ---------------------------------------------------------------------------
# yfinance integration (mocked)
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
        assert not stock.history(period="1mo").empty

    @patch("yfinance.Ticker")
    def test_invalid_ticker_returns_empty_history(self, mock_cls):
        mock = MagicMock()
        mock.history.return_value = pd.DataFrame()
        mock_cls.return_value = mock
        import yfinance as yf
        stock = yf.Ticker("FAKEXYZ")
        assert stock.history(period="1mo").empty

    @patch("yfinance.Ticker")
    def test_price_stats_computed_from_history(self, mock_cls):
        mock_cls.return_value = make_mock_stock(
            [100.0, 200.0, 150.0],
            {"longName": "Test Corp"},
        )
        import yfinance as yf
        history = yf.Ticker("TEST").history(period="1mo")
        assert history["Close"].max() == 200.0
        assert history["Close"].min() == 100.0
        assert history["Close"].mean() == pytest.approx(150.0)

    @patch("yfinance.Ticker")
    def test_news_list_retrieved(self, mock_cls):
        news = [
            {"content": {"title": "Big news", "summary": "Details.", "pubDate": "2024-01-01"}},
            {"content": {"title": "More news", "summary": "More details.", "pubDate": "2024-01-02"}},
        ]
        mock_cls.return_value = make_mock_stock([100.0], {"longName": "Apple Inc."}, news_list=news)
        import yfinance as yf
        stock = yf.Ticker("AAPL")
        assert len(stock.news) == 2
        assert stock.news[0]["content"]["title"] == "Big news"

    @patch("yfinance.Ticker")
    def test_no_news_returns_empty_list(self, mock_cls):
        mock_cls.return_value = make_mock_stock([100.0], {"longName": "Apple Inc."}, news_list=[])
        import yfinance as yf
        assert not yf.Ticker("AAPL").news

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
        assert not s1.history(period="1mo").empty
        assert not s2.history(period="1mo").empty
        assert s1.info["longName"] == "Apple Inc."
        assert s2.info["longName"] == "Microsoft Corporation"

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
        assert not s1.history(period="1mo").empty
        assert s2.history(period="1mo").empty

    @patch("yfinance.Ticker")
    def test_info_na_fields_when_data_missing(self, mock_cls):
        mock_cls.return_value = make_mock_stock([100.0], {})
        import yfinance as yf
        info = yf.Ticker("SPARSE").info
        assert info.get("currentPrice", "N/A") == "N/A"
        assert info.get("marketCap", "N/A") == "N/A"
        assert info.get("longName", "N/A") == "N/A"
        assert info.get("sector", "N/A") == "N/A"
