import yfinance as yf

stock = yf.Ticker("AAPL")

history = stock.history(period="1mo")


# special ticker yfinance object
print(stock)

# stock.info is a dictionary
# print(stock.info["longName"])
# print(stock.info["currentPrice"])
# print(stock.info["sector"])
# print(stock.info["marketCap"])

# history is a dataframe

print(type(history))
print(history.head())

print(history.columns)

print("Highest Close:", history["Close"].max())
print("Lowest Close:", history["Close"].min())
print("Average Close:", history["Close"].mean())