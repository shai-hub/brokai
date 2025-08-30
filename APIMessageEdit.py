from datetime import datetime, timedelta
import pandas as pd
import json

def change_stock_message(file_path, stock_name, Buy_date= datetime.now(),
    Sale_date= datetime.now()+ timedelta(weeks=1), estimate_forecast_date=datetime.now()):
    """
    replace the file path txt with stock name and date
    :param file_path: file path
    :param StocksTable: pandas stocks table
    :param stock_name: relevant stock name
    :return: new contest message
    """
 
    replacements_dict = {
        "Stock Name": stock_name,
        "Buy date": Buy_date.strftime("%Y-%m-%d %H:%M:%S"),
        "Sale date": Sale_date.strftime("%Y-%m-%d %H:%M:%S"),
        "estimate forecast date": estimate_forecast_date.strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    for old_word, new_word in replacements_dict.items():
        content = content.replace(old_word, new_word)

    return content


def change_portfoilo_message(file_path, StocksTable, StockPortfolioTable,
    saleData= datetime.now() - timedelta(days=6),
    newsaleData=datetime.now() + timedelta(weeks=1),
    max_stocks_invest= 5, desired_confidance= 80):
    """
    replace the file path txt with stock name and date
    :param file_path: file path
    :param StocksTable: pandas stocks table
    :param stock_name: relevant stock name
    :return: new contest message
    """

    StocksTable['Sale date'] = pd.to_datetime(StocksTable['Sale date']).normalize()
    StocksTable['Buy date'] = pd.to_datetime(StocksTable['Buy date']).normalize()

    current_potrfoilo = StockPortfolioTable.to_string(index=False)


    StocksTableForcast = StocksTable.loc[StocksTable['Sale date'] == saleData].values[0]
    StocksTableForcast['estimate forecast date'] = \
    StocksTableForcast.to_datetime[StocksTableForcast['estimate forecast date']]
    df_sorted = StocksTableForcast.sort_values(['Stocks Name', 'estimate forecast date'],ascending=[True, False])
    StocksTable= df_sorted.drop_duplicates('Stocks Name', keep= 'first')
    StocksTableStr = StocksTable.drop(["currently in stock portfolio", "portfolio percent"]).to_string(index=False)

    StocksTableUpdateForcast = StocksTable.loc[StocksTable['Sale date'] == newsaleData].values[0]
    StocksTableUpdateForcast['estimate forecast date'] = \
    StocksTableUpdateForcast.to_datatime[StocksTableUpdateForcast['estimate forecast date']]
    df_sorted = StocksTableUpdateForcast.sort_values(['Stocks Name', 'estimate forecast date'],ascending=[True, False])
    StocksTableUpdate= df_sorted.drop_duplicates('Stocks Name', keep= 'first')
    StocksTableUpdateStr = StocksTableUpdate.drop(["currently in stock portfolio", "portfolio percent"]).to_string(index=False)


    replacements_dict = {
        "Sale date": saleData,
        "New sale data": newsaleData,
        "Portfolio management": current_potrfoilo,
        "StocksTable": StocksTableStr,
        "UpdateStocksTable": StocksTableUpdateStr,
        "Maximum Stocks Invest": str(max_stocks_invest),
        "Desired confidence level": str(desired_confidance)
    }

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    for old_word, new_word in replacements_dict.items():
        content = content.replace(old_word, new_word)

    return content

def read_stock_info_response(content):
    json_text = content.choices[0].message.content
    data = json.loads(json_text)
    return data["Exists"],data["Ticker"],data["Name"],data["Market"],data["Sector"],data["User1"],data["User2"],data["User3"],data["User4"],data["User5"],data["User6"] 

def read_stockInital_info_response(content):
    json_text = content.choices[0].message.content
    data = json.loads(json_text)
    return data["up/down"],data["confidence level"],data["stop-loss"]

def read_deepLookStock_info_response(content):
    json_text = content.choices[0].message.content
    data = json.loads(json_text)
    return data["A1"],data["A2"],data["A3"],data["A4"],data["A5"],data["A6"],data["A7"],data["A8"],data["A9"],data["A10"],data["A11"],data["A12"],data["A13"],data["A14"],data["A15"],data["A16"],data["A17"],data["A18"],data["A19"],data["A20"]

def read_portfolio_invest(content):
    json_text = content.choices[0].message.content
    data = json.loads(json_text)
    return json.loads(content)
