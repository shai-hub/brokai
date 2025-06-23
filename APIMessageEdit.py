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
        "Buy date": Buy_date,
        "Sale date": Sale_date,
        "estimate forecast date": estimate_forecast_date
    }

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    for old_word, new_word in replacements_dict.items():
        content = content.replace(old_word, new_word)

    return content


def change_portfoilo_message(file_path, StocksTable,
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

    StocksTable['Sale date'] = pd.to_datatime(StocksTable['Sale date']).normalize()
    StocksTable['Buy date'] = pd.to_datatime(StocksTable['Buy date']).normalize()

    current_potrfoilo = StocksTable.loc[StocksTable['"currently in stock portfolio"'] == 'yes']\
    .values[0]
    current_potrfoilo = current_potrfoilo["Stocks Name","Buy date", "portfolio percent"].to_string(index=False)


    StocksTableForcast = StocksTable.loc[StocksTable['Sale date'] == saleData].values[0]
    StocksTableForcast['estimate forecast date'] = \
    StocksTableForcast.to_datatime[StocksTableForcast['estimate forecast date']]
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

def read_stock_info_response(contant):
    data = json.loads(contant)
    return data["exists"],data["Ticker"],data["Name"],data["Market"],data["Sector"]