import pandas as pd

StockTable = {
    "Stocks Name" : [],
    "Stock volatility forecast": [],
    "Buy date": [],
    "Sale date": [],
    "estimate forecast date": [],
    "Confidence level": [],
    "Recommended stop-loss": [],
    "currently in stock portfolio": [],
    "portfolio percent": []
}

df = pd.DataFrame(StockTable).astype({
    "Stocks Name": "string",
    "Stock volatility forecast": "int32",
    "Buy date": "datetime64[ns]",
    "Sale date": "datetime64[ns]",
    "estimate forecast date": "datetime64[ns]",
    "Confidence level": "int32",
    "Recommended stop-loss": "int32"
})

df.to_excel("StocksTable.xlsx", index=False)


df1 = pd.DataFrame(StockPortfolioTable).astype({
    "Stocks Name": [],
    "Buy date": [],
    "Confidence level": [],
    "Recommended stop-loss": [],
    "portfolio split": []
})

StockPortfolioTable = {
    "Stocks Name": "string",
    "Buy date": "datetime64[ns]",
    "Confidence level":  "int32",
    "Recommended stop-loss": "int32",
    "portfolio split": "int32"
}

df1.to_excel("StockPortfolioTable.xlsx", index=False)
