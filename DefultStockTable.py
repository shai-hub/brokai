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
    "currently in stock portfolio": "string",
    "Stock volatility forecast": "int32",
    "Buy date": "datetime64[ns]",
    "Sale date": "datetime64[ns]",
    "estimate forecast date": "datetime64[ns]",
    "Confidence level": "int32",
    "Recommended stop-loss": "int32"
})

df.to_excel("StocksTable.xlsx", index=False)


StockHistoryForcastEstimateTable = {
    "Stock volatility forecast": [],
    "Start date": [],
    "End date": [],
    "estimate forecast date": [],
    "Confidence level": [],
    "Recommended stop-loss": []
}

df1 = pd.DataFrame(StockHistoryForcastEstimateTable).astype({
    "Stock volatility forecast": "int32",
    "Start date": "datetime64[ns]",
    "End date": "datetime64[ns]",
    "estimate forecast date": "datetime64[ns]",
    "Confidence level": "int32",
    "Recommended stop-loss": "int32"
})

with pd.ExcelWriter("StocksForcastHistory.xlsx") as writer:
    df1.to_excel(writer, sheet_name='ARYT', index=False)
    df1.to_excel(writer, sheet_name='AAPL', index=False)