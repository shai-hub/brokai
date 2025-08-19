# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from StockManagement import StockManagement
from clientProtfolio import clientProtfolio
from client import NewModelClientPortfolio
from clientManagement import clientManagement
from openai import OpenAI
import pandas as pd
from datetime import datetime, timedelta
import os


# p = NewModelClientPortfolio(api_key)
# client_id = "C001"
# p.add_trade_for_client(client_id, "AAPL", "US", "BUY", 10, 180.00, datetime(2025,8,1,14,0))
sm = StockManagement(api_key)
cp = clientManagement(sm)
cp.Clientpredict("C001")
#
# # Load existing client workbook (if exists), then add trades and auto-save each time
# p.add_trade_for_client(client_id, "AAPL", "US", "BUY", 10, 180.00, datetime(2025,8,1,14,0))
# p.add_trade_for_client(client_id, "ILCO", "IL", "BUY", 100, 6400.0, datetime(2025,8,4,9,45))
#
# # Show portfolio snapshot (auto-load happened earlier)
# p.pretty_portfolio_print(client_id)
#
# # Save workbook explicitly (optional—add_trade_for_client already saved)
# p.save_client_excel(client_id)
# print("Saved workbook to:", p._client_path(client_id))
#
# # Later: client buys more — same ID, same file will be updated
# p.add_trade_for_client(client_id, "AAPL", "US", "BUY", 3, 188.00, datetime(2025,8,13,10,0))
# p.pretty_portfolio_print(client_id)
# print("Updated workbook:", p._client_path(client_id))
#
#
# customerProtfolio = StockManagement(api_key)
# idoProtflio = clientProtfolio(customerProtfolio)
# idoProtflio.add_stock(1234 , "L", datetime.now())
#
# idoProtflio.Recommended_stocks("Energy")
#
# buyTime = datetime(2024,8,4,4)
# sellTime = datetime.now()
# customerProtfolio.get_forcast_stock(customerProtfolio.client,"Texas Instruments Inc.", buyTime, sellTime)
# print("0")
#
#
# client = OpenAI(api_key= 'api_key')
# response = client.responses.create(
#     model="gpt-3.5-turbo",
#     input="Write a one-sentence bedtime story about a unicorn."
# )
#
# print(response.output_text)
