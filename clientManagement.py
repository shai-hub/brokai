import pandas as pd
import os
from brokai.StockManagement import StockManagement
from brokai.client import NewModelClientPortfolio
from datetime import datetime, timedelta
import random
import string

# ------------------------------
# Utility: create a short random run/serial ID
# Used to tag forecast/grade batches so you can retrieve rows for the same run.
# ------------------------------
def generate_serial(length: int = 12) -> str:
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))


class clientManagement:
    """
    High-level manager that ties your AI layer (StockManagement) to:
      - a client portfolio implementation (NewModelClientPortfolio) for holdings
      - XLSX tables produced by your AI (StocksTable.xlsx, DeepTable.xlsx)
      - convenience workflows: recommend, predict for a client, deep grade

    NOTE:
    - This class EXPECTS that:
        • 'StocksTable.xlsx' is where get_forcast_stock writes its outputs
        • 'DeepTable.xlsx' is where deepStock writes its outputs
        • 'stock_lists.xlsx' contains the universe you want to scan (with columns like Sector, Market, Name)
    - It also calls self.load_data() / self.save_data() in delete_stock(), which are NOT defined here.
      If you still want delete_stock() to edit some client-stock mapping file, add those methods or remove delete_stock().
    """

    def __init__(self,
                 AImanage: StockManagement,
                 stock_lists: str = "stock_lists.xlsx",
                 stocksTable: str = "StocksTable.xlsx",
                 deepLook: str = "DeepTable.xlsx"):
        """
        Initialize the manager.

        Args:
            AImanage: your StockManagement instance (AI brain).
            stock_lists: path to the XLSX with your stock universe to scan.
            stocksTable: path to the XLSX where AI forecasts are written.
            deepLook: path to the XLSX where deep analysis is written.
        """
        # Portfolio frontend you wrote elsewhere; used to fetch current holdings by client.
        self.clientManagement = NewModelClientPortfolio(AImanage)

        # Schema this class historically used for a separate client<->stock mapping sheet.
        # (Not directly used below unless you add load_data/save_data again.)
        self.columns = ["ClientID", "Ticker", "Name", "BuyDate"]

        # Pre-load the data files you refer to later.
        # If a file is missing, you may want to guard with os.path.exists to avoid FileNotFoundError.
        self.stock_lists = pd.read_excel(stock_lists)
        self.stocksTable = pd.read_excel(stocksTable)
        self.deepLook = pd.read_excel(deepLook)

        # Keep a reference to the AI
        self.AImanage = AImanage

    # ------------------------------
    # OPTIONAL — Helper so your existing self.generate_serial() calls keep working.
    # (They were calling a method that didn't exist before.)
    # ------------------------------
    def generate_serial(self, length: int = 12) -> str:
        """Proxy to the module-level generate_serial()."""
        return generate_serial(length)

    # ------------------------------
    # CRUD-style method (currently depends on missing load_data/save_data).
    # If you want this to work, implement:
    #   def load_data(self): ...
    #   def save_data(self, df): ...
    # to read/write the mapping file that has columns self.columns.
    # ------------------------------
    def delete_stock(self, client_id, stock_name):
        """
        Remove a stock from a specific client's mapping file.

        Requirements:
            - self.load_data() must return a DataFrame with at least columns:
              ["ClientID", "Ticker", "Name", "BuyDate"]
            - self.save_data(df) must overwrite that file.

        Side effects:
            - Persists the updated mapping to disk via self.save_data(df).

        NOTE: This method will raise AttributeError unless you implement load_data/save_data.
        """
        df = self.load_data()  # <-- NOT defined in this class; implement if you want to use delete_stock
        condition = (df["ClientID"] == client_id) & (df["Name"] == stock_name)
        if not condition.any():
            print(f"No such stock {stock_name} for client {client_id}.")
            return
        df = df[~condition]
        self.save_data(df)
        print(f"Deleted stock {stock_name} for client {client_id}.")

    # ------------------------------
    # Recommendation workflow
    # ------------------------------
    def Recommended_stocks(self,
                           sector: str = "ALL",
                           market: str = "US",
                           sale_date: datetime = None,
                           confidencePresentage: int = 70):
        """
        Run AI forecasts for every stock in stock_lists that matches (sector, market),
        then pull the top 3 recommendations from StocksTable.xlsx for this run.

        Args:
            sector: filter by sector; "ALL" means do not filter.
            market: "US", "IL", etc. Must match the 'Market' column in stock_lists.
            sale_date: horizon end date used in get_forcast_stock(). Defaults to +365 days.
            confidencePresentage: minimum 'Confidence level' to keep in the final list.

        Returns:
            DataFrame of the top 3 recommendations (sorted by 'Stock volatility forecast' then 'Confidence level').

        Side effects:
            - Calls self.AImanage.get_forcast_stock(...) for each (sector, market) match.
            - Reads 'StocksTable.xlsx' to retrieve rows for this run (matched by timestamp+serial).
        """
        sale_date = sale_date or (datetime.now() + timedelta(days=365))
        SN = self.generate_serial()  # run identifier so you can filter rows that belong to THIS pass
        df = self.stock_lists
        predict_time = datetime.now().replace(second=0, microsecond=0)

        # Kick off forecasts for eligible rows in your universe sheet
        for _, row in df.iterrows():
            if ((row['Sector'] == sector or sector == "ALL") and row['Market'] == market):
                self.AImanage.get_forcast_stock(
                    self.AImanage.client,
                    row['Name'],
                    predict_time,
                    sale_date,
                    SN
                )

        # Pull back the results for THIS run from the AI output file
        df2 = pd.read_excel("StocksTable.xlsx")
        # match the 'Buy date' formatting convention used by your AI output writer
        run_key = predict_time.strftime('%Y-%m-%d %H:%M.%f')[:-3]

        recStock = df2[
            (df2['Buy date'] == run_key) &
            (df2["Confidence level"] >= confidencePresentage) &
            (df2["Serial number"] == SN)
        ]

        sorted_recStock = recStock.sort_values(
            ["Stock volatility forecast", "Confidence level"],
            ascending=[False, False]
        )

        print(sorted_recStock.head(3))
        # Refresh the in-memory stock_lists from file if that's your convention
        self.stock_lists = pd.read_excel("StocksTable.xlsx")

        return sorted_recStock.head(3)

    # ------------------------------
    # Predict for a client based on CURRENT HOLDINGS
    # ------------------------------
    def Clientpredict(self, ID, sale_date: datetime = None):
        """
        Run AI forecasts for ALL open holdings of a given client, as reported by
        NewModelClientPortfolio.get_client_holdings(ID), and return the rows for this run.

        Args:
            ID: client identifier (string or int).
            sale_date: horizon end date; defaults to +30 days.

        Returns:
            DataFrame of all forecast rows from 'StocksTable.xlsx' for this run (matched by Serial number).

        Assumptions:
            - self.clientManagement.get_client_holdings(ID) returns a DataFrame with at least a 'ticker' column.
            - self.AImanage.get_forcast_stock(...) writes rows into 'StocksTable.xlsx' including 'Serial number'.
        """
        sale_date = sale_date or (datetime.now() + timedelta(days=30))
        SN = generate_serial()  # using module-level helper here (both are fine)

        # Get current holdings for the client from your portfolio layer
        df = self.clientManagement.get_client_holdings(ID)

        # For each holding, run a forecast from NOW -> sale_date
        for _, row in df.iterrows():
            # Here you use 'ticker' directly (vs. 'Name'); make sure your AI expects a ticker.
            self.AImanage.get_forcast_stock(
                self.AImanage.client,
                row['ticker'],
                datetime.now(),
                sale_date,
                SN
            )

        # Return only the rows for this run
        df2 = pd.read_excel("StocksTable.xlsx")
        RelStock = df2[df2['Serial number'] == SN]
        print(RelStock)

        # Optional: refresh in-memory copy if you rely on it elsewhere
        self.stock_lists = pd.read_excel("StocksTable.xlsx")

        return RelStock

    # ------------------------------
    # Deep grade for a single stock
    # ------------------------------
    def StockGrade(self, stock_name: str) -> str:
        """
        Run the deep analysis for a single stock, sum A1..A20, and map to a status label.

        Args:
            stock_name: name/ticker to analyze (must be what your AI expects).

        Returns:
            A text label ("Stock Status: Excellent/Strong/Stable/Weak/Very Weak") based on total points.

        Side effects:
            - Calls self.AImanage.deepStock(...) which should write one row into 'DeepTable.xlsx' for this run.
            - Reads 'DeepTable.xlsx' and filters rows by this run's Serial number.
        """
        SN = self.generate_serial()
        today_time = datetime.now().replace(second=0, microsecond=0)

        # Trigger the AI deep analysis (expected to write into DeepTable.xlsx with the same SN)
        self.AImanage.deepStock(self.AImanage.client, stock_name, today_time, SN)

        # Read results for just this run
        self.deepLook = pd.read_excel("DeepTable.xlsx")
        df = pd.read_excel("DeepTable.xlsx")
        df = df[df['Serial number'] == SN]

        # Safety: ensure we actually got a row
        if df.empty:
            print("No deep analysis rows found for this run.")
            return "Stock Status: Unknown"

        # Sum the binary/point questions A1..A20 (must exist in your file)
        grade = df.loc[:, 'A1':'A20'].sum(axis=1).iloc[0]

        # Map the score to a regulator-safe label (no 'Buy'/'Sell' wording)
        if grade >= 17:
            print("Stock Status: Excellent")
            return "Stock Status: Excellent"
        elif grade >= 14:
            print("Stock Status: Strong")


