from datetime import datetime, timedelta
import pandas as pd
from  APIMessageEdit import *

class StockManagement:
    def __init__(self, stock_lists: pd.DataFrame, stocksTable: pd.DataFrame):
        self.stock_lists= stock_lists.copy()
        self.stocksTable= stocksTable.copy()

    def printHistoryStockForcast(self, StockName):  # print stock current table us
        result = self.stocksTable[self.stocksTable["Stocks Name"] == StockName]
        result= result.drop(["currently in stock portfolio", "portfolio percent"]).to_string(index=False)
        print(result)

    def add_stock_to_list(self, client, StockName):
        if not StockName.isalpha():
            raise ValueError("StockName must contain only letters")

        content = change_stock_message("ChatQuastions/StockInfo.txt",StockName)
        response = client.responses.create(
            model="gpt-3.5-turbo",
            input=content
        )

        exists,Ticker,Name, Market,Sector = read_stock_info_response(response)
        if (exists=='yes'):
            # check if already excicts in the table
            exists = ((self.stock_lists["Ticker"] == Ticker)).any()

            if not exists:
                self.stock_lists.loc[len(self.stock_lists)] = [Ticker,Name, Market,Sector]
                self.stock_lists.to_excel("StocksTable.xlsx", index=False)
            else:
                print("this stock with the current sale date already exits")
            self.stock_lists.to_excel("stock_lists.xlsx", index=False)

    def get_forcast_stock(self, client, stock_name, buy_date, sale_date):
        file_path= "ChatQuastions/StockInitialForcast.txt"
        estimate_forecast_date = datetime.now()
        contant= change_stock_message(file_path, stock_name, buy_date, sale_date, estimate_forecast_date)
