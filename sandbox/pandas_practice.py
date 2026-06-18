import pandas as pd

data = {
    "Ticker": ["AAPL", "MSFT", "GOOG"],
    "Price": [215, 500, 180]
}

# Data frame is like a full on table, basically a spreadsheet.
# A series is one column from the spreadsheet
# this method is used when the data is already in memory like the dictionary in this file
# df = pd.DataFrame(data)

# this is used when data lives in a file much more like reading a data frame
df = pd.read_csv("stocks.csv")

#Shows the first 5 rows of your table
# Usually the first thing ppl do just to peak what the data looks like
# You can also choose how many rows to see "print(df.head(10))"
print(df.head()) 

# shows the last 5 rows
print(df.tail())

# Shows you the names of all your columns
print(df.columns)

# Tells youu how big your table is in the form of "(rows, columns)"
print(df.shape)

# Accessing a column. the type of it is a series because each column within a dataframe
# is a series. They differ from lists because they have special functions like max, mean and min
# You can still access each value in the column/series with indexes: "print(df["Price"][0])"
print(df["Price"].max())

# "df["Price"] > 200" returns a boolean series of just true and false
# and since print(df) prints the entire dataframe if you add these boolean conditions
# it will only return the dataframe with the specified rows as true
print(df[df["Price"] > 200])