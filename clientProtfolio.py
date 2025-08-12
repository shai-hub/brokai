import pandas as pd
import os
from StockManagement import StockManagement
from datetime import datetime, timedelta
import random
import string



class clientProtfolio:
    

    def __init__(self, AImanage : StockManagement, stock_lists = "stock_lists.xlsx" , stocksTable = "StocksTable.xlsx", StockPortfolioTable = "StockPortfolioTable.xlsx" , filename="client_portfolio.xlsx"):
        self.filename= filename 
        self.columns= ["ClientID", "Name", "BuyDate"]
        self.stock_lists= pd.read_excel(stock_lists)
        self.stocksTable= pd.read_excel(stocksTable)
        self.AImanage= AImanage 
        # Create the Excel file if it doesn't exist
        if not os.path.exists(self.filename):
            df = pd.DataFrame(columns=self.columns)
            df.to_excel(self.filename, index=False)

    def load_data(self):
        return pd.read_excel(self.filename)
    def generate_serial(self, length=12):
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def save_data(self, df):
        df.to_excel(self.filename, index=False)

    def add_stock(self, client_id, stock_name, buy_date):
        df = self.load_data()
        stock_name , exists = self.AImanage.add_stock_to_list(self.AImanage.client, stock_name)
        
        if (exists): 
            # Check if the stock already exists for this client
            if ((df["ClientID"] == client_id) & (df["Name"] == stock_name)).any():
                print(f"Client {client_id} already has stock {stock_name}.")
                return
            df.loc[len(df)] = [client_id, stock_name, buy_date]
            self.save_data(df)
            print(f"Added stock {stock_name} for client {client_id}.")
            return
        print("the stocks dosent exists")

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
                self.AImanage.get_forcast_stock(self.AImanage.client, row['Name'], predict_time, sale_date, SN)
        df2 = pd.read_excel("StocksTable.xlsx")
        recStock = df2[((df2['Buy date']) == predict_time.strftime('%Y-%m-%d %H:%M.%f')[:-3]) & (df2["Confidence level"] >= confidencePresentage) & (df2["Serial number"] == SN) ] 
        sorted_recStock = recStock.sort_values(["Stock volatility forecast","Confidence level" ], ascending=[False,False])
        
        print(sorted_recStock.head(3))
        self.stock_lists= pd.read_excel("StocksTable.xlsx")

        return sorted_recStock.head(3)
        
    def Clientpredict(self , ID , sale_date = datetime.now() + timedelta(days=365)):
        SN = self.generate_serial()
        df = self.load_data()
        predict_time = datetime.now().replace(second=0, microsecond=0)
        for _,row in df.iterrows():
            if row['ClientID'] == ID:
                self.AImanage.get_forcast_stock(self.AImanage.client, row['Name'], row['BuyDate'], sale_date, SN)

        df2 = pd.read_excel("StocksTable.xlsx")
        RelStock = df2[(df2['Serial number']) == SN] 
        print(RelStock)
        self.stock_lists= pd.read_excel("StocksTable.xlsx")

        return RelStock



