from datetime import datetime, timedelta
import pandas as pd
from  brokai.APIMessageEdit import *  # assumes helpers like change_stock_message, read_* are defined here
from openai import OpenAI
import yfinance as yf
import os

class StockManagement:
    """
    Orchestrates:
      - Loading/saving stock universe and AI-produced tables (forecasts, deep analysis, portfolio)
      - Asking the LLM for stock metadata/validation, forecasts, deep dives
      - Pulling financial statements & intraday prices via yfinance for grounding

    Files (expected schema comes from your LLM helpers):
      • stock_lists.xlsx         -> [Ticker, Name, Market, Sector]
      • StocksTable.xlsx         -> (AI forecast outputs; columns used below)
      • DeepTable.xlsx           -> (AI deep-analysis outputs; A1..A20 etc.)
      • StockPortfolioTable.xlsx -> (AI portfolio suggestions; used in get_portfolio_invest)
    """

    def __init__(self, AI_key,
                 stock_lists="stock_lists.xlsx",
                 stocksTable="StocksTable.xlsx",
                 deepTable="DeepTable.xlsx",
                 StockPortfolioTable="StockPortfolioTable.xlsx"):
        """
        Load working tables and create an OpenAI client.

        NOTE: If any file is missing, pd.read_excel will raise FileNotFoundError.
              If you want a softer behavior, guard with os.path.exists and create empty frames.
        """
        # Consider wrapping with exists checks if these files may not exist yet
        self.stock_lists = pd.read_excel(stock_lists)
        self.stocksTable = pd.read_excel(stocksTable)
        self.deepTable = pd.read_excel(deepTable)
        self.StockPortfolioTable = pd.read_excel(StockPortfolioTable)

        # OpenAI client for chat completions
        self.client = OpenAI(api_key=AI_key)

    def printHistoryStockForcast(self, StockName: str) -> None:
        """
        Print historical forecast rows for a given stock name from self.stocksTable.

        Expected columns in self.stocksTable:
          - "Stocks Name"
          - "currently in stock portfolio" (will be dropped)
          - "portfolio percent"            (will be dropped)

        Args:
            StockName: name to filter by (matches 'Stocks Name' column).
        """
        result = self.stocksTable[self.stocksTable["Stocks Name"] == StockName]
        # Drop columns that are presentation-only
        result = result.drop(["currently in stock portfolio", "portfolio percent"], errors="ignore")
        print(result.to_string(index=False))

    def add_stock_to_list(self, client: OpenAI, StockName: str):
        """
        Ask the LLM to validate/find Ticker/Name/Market/Sector for a plain StockName, and
        append it to stock_lists.xlsx if it doesn't already exist.

        Returns:
            tuple: (Name, Ticker, exists_bool) where 'exists_bool' indicates whether the
                   stock was already present in stock_lists BEFORE this call.

        Raises:
            ValueError: if StockName contains non-letter characters (current rule).
        """
        # Basic input guard: only letters (your original rule)
        no_spaces = StockName.replace(" ", "")
        if not no_spaces.isalpha():
            raise ValueError("StockName must contain only letters")

        # Prompt template and LLM call
        content = change_stock_message("ChatQuastions/StockInfo.txt", StockName)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": content}]
        )
        reply = response.choices[0].message.content
        print(reply)

        # Parse LLM response (helper must return these 5 fields)
        exists, Ticker, Name, Market, Sector = read_stock_info_response(response)

        if (exists == 'yes'):
            # Check if already in table by Name (your existing logic)
            already = ((self.stock_lists["Name"] == Name)).any()

            if not already:
                # Append and persist
                self.stock_lists.loc[len(self.stock_lists)] = [Ticker, Name, Market, Sector]
                self.stock_lists.to_excel("stock_lists.xlsx", index=False)
                self.stock_lists = pd.read_excel("stock_lists.xlsx")
                print("The stock has been added to the stock list.")
            else:
                print("This stock already exists in the stock list.")
            return Name, Ticker, already

        # If exists != 'yes' you return None implicitly (same as your original)
        # You could return a sentinel here if you prefer.

    def get_forcast_stock(self, client: OpenAI, stock_name: str,
                          buy_date: datetime, sale_date: datetime, serialNum: str) -> None:
        """
        Ask the LLM for an initial forecast for a given stock (with dates), grounded with
        yfinance financial statements, and append the result to StocksTable.xlsx.

        Args:
            client: OpenAI client
            stock_name: ticker or name (depending on your template expectation)
            buy_date: scenario buy time (string/datetime used for the prompt)
            sale_date: scenario sale time
            serialNum: run tracker for joining output rows

        Side effects:
            - Writes/updates self.stocksTable and saves to "StocksTable.xlsx"
        """
        file_path = "ChatQuastions/StockInitialForcast.txt"
        estimate_forecast_date = datetime.now().replace(second=0, microsecond=0)

        # Filter universe row for grounding (NOTE: your comment says "for old model "Ticker" -> "Name"")
        df = self.stock_lists
        df = df[df["Ticker"] == stock_name]  # If stock_name is actually Name, switch to df["Name"] == stock_name

        # --- Guard: avoid index errors if not found ---
        if df.empty:
            print(f"[WARN] Ticker '{stock_name}' not found in stock_lists. Skipping forecast.")
            return

        # Pass ticker and market to yfinance grounding
        FinancialStat = self.getFinancialStatements(df["Ticker"].iloc[0], df["Market"].iloc[0])

        # Compose the final prompt
        content = change_stock_message(file_path, stock_name, buy_date, sale_date, estimate_forecast_date)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a precise financial data analyst."},
                {"role": "user", "content": f"{FinancialStat}\n\n{content}"}
            ]
        )
        reply = response.choices[0].message.content
        print(reply)

        # Parse outputs (helper must return up_down, confidence_level, stop_loss)
        up_down, confidence_level, stop_loss = read_stockInital_info_response(response)

        # Append a new row. Column order MUST match your actual file schema.
        self.stocksTable.loc[len(self.stocksTable)] = [
            serialNum,
            stock_name,
            up_down,
            buy_date,
            sale_date,
            estimate_forecast_date,
            confidence_level,
            stop_loss,
            [],   # placeholders (you had two list columns)
            []
        ]
        self.stocksTable.to_excel("StocksTable.xlsx", index=False)
        self.stocksTable = pd.read_excel("StocksTable.xlsx")

    def deepStock(self, client: OpenAI, stock_name: str, buy_date: datetime, serialNum: str) -> None:
        """
        Ask the LLM for a deep analysis (20 questions A1..A20), grounded with yfinance statements,
        and append the result to DeepTable.xlsx.

        Args:
            stock_name: input name/ticker as expected by your template
            buy_date: timestamp to include in prompt for context
            serialNum: run ID to link rows to this call

        Side effects:
            - Updates self.deepTable and writes to "DeepTable.xlsx"
        """
        file_path = "ChatQuastions/deeplookStock.txt"

        # Lookup row in universe by NAME (your original code uses Name here)
        df = self.stock_lists
        df = df[df["Name"] == stock_name]

        if df.empty:
            print(f"[WARN] Name '{stock_name}' not found in stock_lists. Skipping deepStock.")
            return

        # Ground with yfinance
        FinancialStat = self.getFinancialStatements(df["Ticker"].iloc[0], df["Market"].iloc[0])

        # Prompt and LLM call
        content = change_stock_message(file_path, stock_name, buy_date)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a precise financial data analyst."},
                {"role": "user", "content": f"{FinancialStat}\n\n{content}"}
            ]
        )
        reply = response.choices[0].message.content
        print(reply)

        # Parse 20 answers
        (A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,
         A11,A12,A13,A14,A15,A16,A17,A18,A19,A20) = read_deepLookStock_info_response(response)

        # Append and persist  (FIX: filename casing -> "DeepTable.xlsx" to match your init)
        self.deepTable.loc[len(self.deepTable)] = [
            serialNum, stock_name,
            A1,A2,A3,A4,A5,A6,A7,A8,A9,A10,
            A11,A12,A13,A14,A15,A16,A17,A18,A19,A20
        ]
        self.deepTable.to_excel("DeepTable.xlsx", index=False)   # FIX from "deepTable.xlsx"
        self.deepTable = pd.read_excel("DeepTable.xlsx")

    def get_portfolio_invest(self, client: OpenAI, sale_date: datetime,
                              max_stock_incest: int, desired_confidence: int):
        """
        Ask the LLM to construct a portfolio (tickers + weights) using your current
        StocksTable and StockPortfolioTable as context.

        NOTE: This function had several typos/bugs in your original:
          - self.StocksTable (capital S) but class uses self.stocksTable
          - .to_datatime -> should be pd.to_datetime
          - df_sorted computed from 'StocksTableForcast' Series (wrong); probably you want to filter/sort a DataFrame
          - Drop/merge lines mixed Series/DataFrame
        I kept the structure but added 'FIX:' comments where needed. You should finish/adjust the
        DataFrame operations according to your actual intended logic.
        """
        file_path = "ChatQuastions/InvestmentPortfolioManagment.txt"

        # FIX: use self.stocksTable (lowercase s) + self.StockPortfolioTable
        content = change_portfoilo_message(
            file_path,
            self.stocksTable,               # FIX
            self.StockPortfolioTable,       # FIX
            saleData=sale_date,
            newsaleData=datetime.now() + timedelta(weeks=1),
            max_stocks_invest=max_stock_incest,     # FIX: name corrected
            desired_confidance=desired_confidence    # (keep original param name expected by template)
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": content}]
        )
        reply = response.choices[0].message.content
        print(reply)

        # Parse dict like {weight%: "Ticker"} or {"Ticker": "weight%"} depending on your helper
        invest_stock_dict = read_portfolio_invest(response)  # <- ensure this returns a dict

        # Build a DataFrame of the allocation
        values_list = list(invest_stock_dict.values())
        key_list = list(invest_stock_dict.keys())
        invest_stock_df = pd.DataFrame({
            'Stocks Name': values_list,     # or 'Ticker' depending on your helper
            "portfolio split": key_list
        })

        # --- The rest of your code below was operating on a Series / wrong column names ---
        # Keep as comments with FIX notes so you can align with your actual schema:

        # Example of filtering your forecasts for the given sale_date:
        # (Make sure 'Sale date' column exists and is datetime)
        # tmp = self.stocksTable.copy()
        # tmp["Sale date"] = pd.to_datetime(tmp["Sale date"], errors="coerce")
        # st_for_sale = tmp[tmp["Sale date"] == sale_date]

        # # If you intend to keep only latest estimate per stock:
        # st_for_sale["estimate forecast date"] = pd.to_datetime(st_for_sale["estimate forecast date"], errors="coerce")
        # df_sorted = st_for_sale.sort_values(["Stocks Name", "estimate forecast date"], ascending=[True, False])
        # stocks_latest = df_sorted.drop_duplicates("Stocks Name", keep="first")

        # # Optional: drop presentation-only column if exists
        # stocks_latest = stocks_latest.drop(columns=["portfolio percent"], errors="ignore")

        # # Merge with the AI portfolio allocation proposal
        # df_merge = pd.merge(stocks_latest, invest_stock_df, on="Stocks Name", how="inner")
        # return df_merge

        # For now, just return the allocation table (so this function returns something consistent)
        return invest_stock_df

    def getFinancialStatements(self, Ticker: str, market="US") -> str:
        """
        Fetch financial statements and last ~30 minutes of 1m bars from Yahoo Finance,
        and return a human-readable text block to embed in LLM prompts.

        Args:
            Ticker: raw ticker without suffix (e.g., 'TEVA' not 'TEVA.TA')
            market: "US" or "IL"; IL adds '.TA' suffix for Yahoo

        Returns:
            str: Text blob including Income Statement, Balance Sheet, Cash Flow, Intraday sample.

        Notes:
            - Yahoo uses trailing '.TA' for Tel Aviv tickers
            - Some tickers may return empty DataFrames; we still format them
        """
        # Add .TA for IL market (simple rule — adjust if you support more exchanges)
        if market == "IL":
            Ticker = f"{Ticker}.TA"

        ticker = yf.Ticker(Ticker)

        # Pull statements (can be empty depending on ticker)
        income_statement = ticker.financials
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow

        # 1-minute intraday prices (sample last ~30 rows)
        intraday_prices = ticker.history(period="1d", interval="1m")

        def df_to_text(df: pd.DataFrame) -> str:
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df.to_string(index=True)
            return "(no data)"

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

    # -------- new model --------
    def Client_add_stock_to_list(self, client: OpenAI, Ticker: str):
        """
        Variant for the “new model”: given a Ticker (letters-only), ask the LLM to
        return (exists, Ticker, Name, Market, Sector) and append to stock_lists if new.

        Returns:
            tuple: (Name, Ticker, exists_bool_in_table) if exists == 'yes'
        """
        # Basic input guard: letters only (like your original)
        no_spaces = Ticker.replace(" ", "")
        if not no_spaces.isalpha():
            raise ValueError("Ticker must contain only letters")

        content = change_stock_message("ChatQuastions/NewModelStockInfo.txt", Ticker)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": content}]
        )
        reply = response.choices[0].message.content
        print(reply)

        exists, Ticker, Name, Market, Sector = read_stock_info_response(response)
        if (exists == 'yes'):
            already = ((self.stock_lists["Name"] == Name)).any()
            if not already:
                self.stock_lists.loc[len(self.stock_lists)] = [Ticker, Name, Market, Sector]
                self.stock_lists.to_excel("stock_lists.xlsx", index=False)
                self.stock_lists = pd.read_excel("stock_lists.xlsx")
                print("The stock has been added to the stock list.")
            else:
                print("This stock already exists in the stock list.")
            return Name, Ticker, already
