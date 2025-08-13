import pandas as pd
import os
from brokai.StockManagement import StockManagement
from brokai.client import NewModelClientPortfolio
from datetime import datetime, timedelta
import random
import string

def generate_serial(length: int = 12) -> str:
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


class clientManagement:

    def __init__(self, AImanage : StockManagement, stock_lists = "stock_lists.xlsx" , stocksTable = "StocksTable.xlsx", deepLook = "DeepTable.xlsx"):
        self.clientManagement= NewModelClientPortfolio(AImanage) 
        self.columns= ["ClientID", "Ticker", "Name" ,"BuyDate"]
        self.stock_lists= pd.read_excel(stock_lists)
        self.stocksTable= pd.read_excel(stocksTable)
        self.deepLook= pd.read_excel(deepLook)
        self.AImanage= AImanage 

    def delete_stock(self, client_id, stock_name):
        df = self.load_data()
        condition = (df["ClientID"] == client_id) & (df["Name"] == stock_name)
        if not condition.any():
            print(f"No such stock {stock_name} for client {client_id}.")
            return
        df = df[~condition]
        self.save_data(df)
        print(f"Deleted stock {stock_name} for client {client_id}.")

    def Recommended_stocks(self, sector = "ALL", market = "US", sale_date = datetime.now() + timedelta(days=365), confidencePresentage = 70):
        SN = self.generate_serial()
        df =  self.stock_lists
        predict_time = datetime.now().replace(second=0, microsecond=0)
        for _,row in df.iterrows():
            if ((row['Sector'] == sector or sector == "ALL" ) and row['Market'] == market ):
                self.AImanage.get_forcast_stock(self.AImanage.client, row['Name'],predict_time, sale_date, SN)
        df2 = pd.read_excel("StocksTable.xlsx")
        recStock = df2[((df2['Buy date']) == predict_time.strftime('%Y-%m-%d %H:%M.%f')[:-3]) & (df2["Confidence level"] >= confidencePresentage) & (df2["Serial number"] == SN) ] 
        sorted_recStock = recStock.sort_values(["Stock volatility forecast","Confidence level" ], ascending=[False,False])
        
        print(sorted_recStock.head(3))
        self.stock_lists= pd.read_excel("StocksTable.xlsx")

        return sorted_recStock.head(3)
        
    def Clientpredict(self , ID , sale_date = datetime.now() + timedelta(days=30)):
        SN = generate_serial()
        df = self.clientManagement.get_client_holdings(ID)
        for _,row in df.iterrows():
            self.AImanage.get_forcast_stock(self.AImanage.client, row['ticker'], datetime.now(), sale_date, SN)

        df2 = pd.read_excel("StocksTable.xlsx")
        RelStock = df2[(df2['Serial number']) == SN] 
        print(RelStock)
        self.stock_lists= pd.read_excel("StocksTable.xlsx")

        return RelStock

    def StockGrade(self, stock_name):
        SN = self.generate_serial()
        today_time = datetime.now().replace(second=0, microsecond=0)
        self.AImanage.deepStock(self.AImanage.client, stock_name, today_time, SN)
        self.deepLook = pd.read_excel("DeepTable.xlsx")
        df = pd.read_excel("DeepTable.xlsx")
        df = df[(df['Serial number']) == SN]
        grade = df.loc[:, 'A1':'A20'].sum(axis=1).iloc[0]
        if grade >= 17:
            print("Stock Status: Excellent")
            return "Stock Status: Excellent"
        elif grade >= 14:
            print("Stock Status: Strong")
            return "Stock Status: Strong"
        elif grade >= 10:
            print("Stock Status: Stable")
            return "Stock Status: Stable"
        elif grade >= 6:
            print("Stock Status: Weak")
            return "Stock Status: Weak"
        else:
            print("Stock Status: Very Weak")
            return "Stock Status: Very Weak"


