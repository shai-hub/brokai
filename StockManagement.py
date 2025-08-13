from datetime import datetime, timedelta
import pandas as pd
from  brokai.APIMessageEdit import *
from openai import OpenAI
import yfinance as yf
import os

class StockManagement:
  
    def __init__(self,  AI_key, stock_lists = "stock_lists.xlsx" , stocksTable = "StocksTable.xlsx", deepTable = "DeepTable.xlsx", StockPortfolioTable = "StockPortfolioTable.xlsx"):
        self.stock_lists= pd.read_excel(stock_lists)
        self.stocksTable= pd.read_excel(stocksTable)
        self.deepTable= pd.read_excel(deepTable)
        self.StockPortfolioTable = pd.read_excel(StockPortfolioTable)
        self.client = OpenAI(api_key= AI_key)
   
    def printHistoryStockForcast(self, StockName):  # print stock current table us
        result = self.stocksTable[self.stocksTable["Stocks Name"] == StockName]
        result= result.drop(["currently in stock portfolio", "portfolio percent"]).to_string(index=False)
        print(result)

    def add_stock_to_list(self, client, StockName):
        no_spaces = StockName.replace(" ", "")
        if not no_spaces.isalpha():
            raise ValueError("StockName must contain only letters")

        content = change_stock_message("ChatQuastions/StockInfo.txt",StockName)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[ {"role": "user", "content":  content} ])
        reply = response.choices[0].message.content
        print(reply)

        exists,Ticker,Name, Market,Sector = read_stock_info_response(response)
        if (exists=='yes'):
            # check if already excites in the table
            exists = ((self.stock_lists["Name"] == Name)).any()

            if not exists:
                self.stock_lists.loc[len(self.stock_lists)] = [Ticker,Name, Market,Sector]
                self.stock_lists.to_excel("stock_lists.xlsx", index=False)
                self.stock_lists = pd.read_excel("stock_lists.xlsx")
                print("The stock has been added to the stock list.")

            else:
                print("this stock with the current sale date already exits.")
            return Name , Ticker, exists
        
    def get_forcast_stock(self, client, stock_name, buy_date, sale_date, serialNum):
        file_path= "ChatQuastions/StockInitialForcast.txt"
        estimate_forecast_date =  datetime.now().replace(second=0, microsecond=0)
        df = self.stock_lists
        df = df[df["Ticker"] == stock_name] #for old model "Ticker" -> "Name"
        FinancialStat = self.getFinancialStatements(df["Ticker"].iloc[0], df[["Market"]].values)
        content= change_stock_message(file_path, stock_name, buy_date, sale_date, estimate_forecast_date)
        response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[   {"role": "system", "content": "You are a precise financial data analyst."}, {"role": "user", "content":   f"{FinancialStat}\n\n{content}"} ])
        reply = response.choices[0].message.content
        print(reply)   
        up_down, confidence_level, stop_loss= read_stockInital_info_response(response)
        self.stocksTable.loc[len(self.stocksTable)] = [serialNum, stock_name, up_down, buy_date, sale_date,
                                                    estimate_forecast_date, confidence_level, stop_loss,[],[]]
        self.stocksTable.to_excel("StocksTable.xlsx", index=False)
        self.stocksTable= pd.read_excel("StocksTable.xlsx")
#check ?
    def deepStock(self, client, stock_name, buy_date, serialNum):
        file_path= "ChatQuastions/deeplookStock.txt"
        df = self.stock_lists
        df = df[df["Name"] == stock_name]
        FinancialStat = self.getFinancialStatements(df["Ticker"].iloc[0], df[["Market"]].values)
        
        content= change_stock_message(file_path, stock_name, buy_date)
        response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[   {"role": "system", "content": "You are a precise financial data analyst."}, {"role": "user", "content":   f"{FinancialStat}\n\n{content}"} ])
        reply = response.choices[0].message.content
        print(reply)   
        A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12,A13,A14,A15,A16,A17,A18,A19,A20 = read_deepLookStock_info_response(response)
        self.deepTable.loc[len(self.deepTable)] = [serialNum, stock_name, A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,A11,A12,A13,A14,A15,A16,A17,A18,A19,A20]
        self.deepTable.to_excel("deepTable.xlsx", index=False)
        self.deepTable= pd.read_excel("deepTable.xlsx")

    def get_portfolio_invest(self, client, sale_date, max_stock_incest, desired_confidence):
        file_path= "ChatQuastions/InvestmentPortfolioManagment.txt"
        content= change_portfoilo_message(file_path, self.StocksTable, self.StockPortfolioTable,
                                 saleData= sale_date, newsaleData=datetime.now() + timedelta(weeks=1),
                                 max_stocks_invest= max_stock_incest, desired_confidance= desired_confidence)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[ {"role": "user", "content":  content} ])
        reply = response.choices[0].message.content
        print(reply) 
        invest_stock_dict= read_portfolio_invest(response) #check if return dic
        values_list = list(invest_stock_dict.values())
        key_list = list(invest_stock_dict.keys())
        invest_stock_df = pd.DataFrame({
        'Stocks Name': values_list,
        "portfolio split": key_list})
        StocksTableForcast = self.StocksTable.loc[self.StocksTable['Sale date'] == sale_date].values[0]
        StocksTableForcast['estimate forecast date'] = \
            StocksTableForcast.to_datatime[StocksTableForcast['estimate forecast date']]
        df_sorted = StocksTableForcast.sort_values(['Stocks Name', 'estimate forecast date'], ascending=[True, False])
        StocksTable= df_sorted.drop_duplicates('Stocks Name', keep= 'first')
        StocksTable = StocksTable.drop([ "portfolio percent"]).to_string(index=False)

        df_merge = pd.merge(StocksTable, invest_stock_df, on= 'Stocks Name', how='inner')

    def getFinancialStatements(self, Ticker, market = "US"):
        if market == "IL":
            Ticker = Ticker + ".TA"

        ticker = yf.Ticker(Ticker)
        income_statement = ticker.financials
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow

        intraday_prices = ticker.history(period="1d", interval="1m")
        
        def df_to_text(df):
            return df.to_string(index=True)
                
        data_text = f"""
        === Income Statement ===
        {df_to_text(income_statement)}

        === Balance Sheet ===
        {df_to_text(balance_sheet)}

        === Cash Flow ===
        {df_to_text(cash_flow)}

        === Intraday Prices (1 min) ===
        {df_to_text(intraday_prices.tail(30))}  # last ~30 minutes
        """

        return data_text




#--------new model----------------------

    def Client_add_stock_to_list(self, client, Ticker):
        no_spaces = Ticker.replace(" ", "")
        if not no_spaces.isalpha():
            raise ValueError("Ticker must contain only letters")

        content = change_stock_message("ChatQuastions/NewModelStockInfo.txt",Ticker)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[ {"role": "user", "content":  content} ])
        reply = response.choices[0].message.content
        print(reply)

        exists,Ticker,Name, Market,Sector = read_stock_info_response(response)
        if (exists=='yes'):
            # check if already excites in the table
            exists = ((self.stock_lists["Name"] == Name)).any()

            if not exists:
                self.stock_lists.loc[len(self.stock_lists)] = [Ticker,Name, Market,Sector]
                self.stock_lists.to_excel("stock_lists.xlsx", index=False)
                self.stock_lists = pd.read_excel("stock_lists.xlsx")
                print("The stock has been added to the stock list.")

            else:
                print("this stock with the current sale date already exits.")
            return Name , Ticker, exists
        