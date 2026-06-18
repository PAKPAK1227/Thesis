import yfinance as yf
import matplotlib.pyplot as plt

ticker = input("Please enter a stock ticker: ").upper().strip()

stock = yf.Ticker(ticker)
history = stock.history(period = "1mo")

# for an invalid ticker history.empty returns true
if history.empty:
    print("Invalid Stock ticker")
else:
    company_name = stock.info["longName"]
    sector = stock.info["sector"]
    current_price = stock.info["currentPrice"]
    market_cap = stock.info["marketCap"]
    h_close = history["Close"].max()
    l_close = history["Close"].min()
    avg_close = history["Close"].mean()

    print("\n--- Stock Summary ---")
    print(f"Company name:  {company_name}")
    print(f"Sector: {sector}")
    

    if current_price != "N/A":
        print(f"Current Price: ${current_price:,.2f}")
    else:
        print("Current Price: N/A")

    if market_cap != "N/A":
        print(f"Market Cap: ${market_cap:,.0f}")
    else:
        print("Market Cap: N/A")

    print(f"Highest close: ${h_close:,.2f}")
    print(f"Lowest close: ${l_close:,.2f}")
    print(f"Average close: ${avg_close:,.2f}")

    history[["Open", "Close"]].plot()
    plt.title("Open vs Close")

    # plt.title("AAPL Closing Prices - Last Month")
    # plt.xlabel("Date")
    # plt.ylabel("Price ($)")
    plt.show()

