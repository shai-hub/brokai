import pandas as pd

StockTable = {
    "Serial number" : [],
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




StockPortfolioTable = {
    "Stocks Name": [],
    "Buy date": [],
    "Confidence level": [],
    "Recommended stop-loss": [],
    "portfolio split": []
}

df1 = pd.DataFrame(StockPortfolioTable).astype({
    "Stocks Name": "string",
    "Buy date": "datetime64[ns]",
    "Confidence level":  "int32",
    "Recommended stop-loss": "int32",
    "portfolio split": "int32"
})

df1.to_excel("StockPortfolioTable.xlsx", index=False)



DeepTable = {
    "Serial number" : [],
    "Stocks Name" : [],
    "A1" : [],
    "A2" : [],
    "A3" : [],
    "A4" : [],
    "A5" : [],
    "A6" : [],
    "A7" : [],
    "A8" : [],
    "A9" : [],
    "A10" : [],
    "A11" : [],
    "A12" : [],
    "A13" : [],
    "A14" : [],
    "A15" : [],
    "A16" : [],
    "A17" : [],
    "A18" : [],
    "A19" : [],
    "A20" : []
}

df = pd.DataFrame(DeepTable).astype({
    "Serial number": "string",
    "Stocks Name": "string",
    "A1" : "int32",
    "A2" : "int32",
    "A3" : "int32",
    "A4" : "int32",
    "A5" : "int32",
    "A6" : "int32",
    "A7" : "int32",
    "A8" : "int32",
    "A9" : "int32",
    "A10" : "int32",
    "A11" : "int32",
    "A12" : "int32",
    "A13" : "int32",
    "A14" : "int32",
    "A15" : "int32",
    "A16" : "int32",
    "A17" : "int32",
    "A18" : "int32",
    "A19" : "int32",
    "A20" : "int32"
})

df.to_excel("DeepTable.xlsx", index=False)
