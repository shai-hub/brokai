# client_portfolio.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from StockManagement import StockManagement
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import os
import random
import string
import os  # (duplicate import is harmless, you can remove this)

# ---------- Helpers ----------
def normalize_ticker(ticker: str, market: str) -> str:
    """
    Normalize a user/DB ticker to the Yahoo Finance symbol for the given market.
    - Adds '.TA' suffix for Israeli (TASE) tickers because Yahoo uses that pattern.
    """
    t = str(ticker).strip().upper()
    m = str(market).strip().upper()
    if m == "IL" and not t.endswith(".TA"):
        t += ".TA"
    return t

def latest_close_yf(ticker: str) -> Optional[float]:
    """
    Get the most recent (delayed) price from Yahoo via yfinance.
    Tries intraday 1m first; falls back to the latest daily close.
    Returns None if no data.
    """
    try:
        tk = yf.Ticker(ticker)
        # Try 1-minute intraday (works only for active sessions / recently active symbols)
        intraday = tk.history(period="1d", interval="1m")
        if isinstance(intraday, pd.DataFrame) and not intraday.empty:
            val = intraday["Close"].dropna()
            if not val.empty:
                return float(val.iloc[-1])
        # Fallback to daily
        daily = tk.history(period="5d", interval="1d")
        if isinstance(daily, pd.DataFrame) and not daily.empty:
            val = daily["Close"].dropna()
            if not val.empty:
                return float(val.iloc[-1])
    except Exception:
        # Swallow network/parse errors and return None (caller handles)
        pass
    return None


# ---------- Data model ----------
@dataclass
class Trade:
    """
    A single executed trade (no shorts allowed in the PnL logic).
    - client_id: portfolio owner
    - ticker: normalized symbol (e.g., 'AAPL' or 'TEVA.TA')
    - market: 'US' or 'IL' (you can extend)
    - side: 'BUY' or 'SELL'
    - qty: shares/contracts (positive)
    - price: execution price per share
    - trade_time: timestamp of the trade
    """
    client_id: str
    ticker: str
    market: str
    side: str
    qty: float
    price: float
    trade_time: datetime


# ---------- Portfolio ----------
class NewModelClientPortfolio:
    """
    Manage client trades and positions with FIFO matching and delayed Yahoo prices.

    Responsibilities:
    - Store trades in-memory (self.trades)
    - Compute realized PnL (closed lots) and unrealized PnL (open lots)
    - Persist a per-client Excel workbook (Trades / Holdings / RealizedPnL / Totals)
    - (Optional) Register tickers in your AI universe via StockManagement

    NOTE:
    - This class assumes 'xlsxwriter' is installed for Excel writing.
      If not, `pip install xlsxwriter` (or switch engine to 'openpyxl').
    """

    def __init__(self, StockManagement):
        """
        Args:
            StockManagement: an instance of your brokai.StockManagement class
                             (used for Client_add_stock_to_list).
        """
        # Trade store (all clients)
        self.trades = pd.DataFrame(columns=[
            "client_id","ticker","market","side","qty","price","trade_time"
        ])
        # Realized PnL ledger is rebuilt on each compute_positions()
        self.realized_ledger = pd.DataFrame(columns=[
            "client_id","ticker","market","trade_time","qty_sold","proceeds","cost","realized_pnl"
        ])
        # Keep a handle to your AI management layer
        self.AImanage = StockManagement

        # Folder for per-client Excel files
        self.storage_dir = "clients_portfolios"
        os.makedirs(self.storage_dir, exist_ok=True)

    # ---------- Paths ----------
    def _client_path(self, client_id: str) -> str:
        """
        Build the absolute path for a client workbook.
        """
        safe_id = str(client_id).replace("/", "_").replace("\\", "_")
        return os.path.join(self.storage_dir, f"{safe_id}_portfolio.xlsx")

    # ---------- Load existing client workbook (if any) ----------
    def ensure_client_loaded(self, client_id: str):
        """
        Merge a client's saved Trades from their Excel workbook into memory (deduped).

        Side-effects:
            - If 'clients_portfolios/<client>_portfolio.xlsx' exists, reads 'Trades' sheet
              and appends into self.trades, dropping exact duplicates across all columns.
        """
        path = self._client_path(client_id)
        if not os.path.exists(path):
            return

        xl = pd.read_excel(path, sheet_name=None)
        if "Trades" not in xl:
            return

        trades = xl["Trades"].copy()
        if trades.empty:
            return

        if "trade_time" in trades.columns:
            trades["trade_time"] = pd.to_datetime(trades["trade_time"])

        self.trades = pd.concat([self.trades, trades], ignore_index=True)
        # De-duplicate by all trade columns (acts like id-less upsert)
        self.trades.drop_duplicates(
            subset=["client_id","ticker","market","side","qty","price","trade_time"],
            inplace=True
        )

    # ---------- CRUD ----------
    def add_trade(self, client_id: str, ticker: str, market: str,
                  side: str, qty: float, price: float,
                  trade_time: Optional[datetime] = None):
        """
        Add a new BUY/SELL to the in-memory trades table (no file I/O).

        Raises:
            AssertionError if side invalid or qty/price non-positive.

        Tip:
            Call save_client_excel(client_id) after batches if you pass autosave=False
            in add_trade_for_client() for performance.
        """
        side_u = str(side).strip().upper()
        assert side_u in ("BUY","SELL"), "side must be BUY or SELL"
        assert qty > 0 and price >= 0, "qty>0 and price>=0 required"
        trade_time = trade_time or datetime.utcnow()

        t_norm = normalize_ticker(ticker, market)
        row = {
            "client_id": client_id,
            "ticker": t_norm,
            "market": str(market).strip().upper(),
            "side": side_u,
            "qty": float(qty),
            "price": float(price),
            "trade_time": trade_time
        }
        # Append without concat warning
        self.trades.loc[len(self.trades)] = row

    def add_trade_for_client(self, client_id: str, ticker: str, market: str,
                             side: str, qty: float, price: float,
                             trade_time: Optional[datetime] = None,
                             autosave: bool = True):
        """
        Convenience: load client's prior Trades (if any), register the ticker in your
        AI stock list, add trade, and optionally refresh & save the Excel workbook.

        Side-effects:
            - Calls AImanage.Client_add_stock_to_list(self.AImanage.client, ticker)
              so your universe stays updated in stock_lists.xlsx
            - When autosave=True, writes the 4-sheet workbook to disk.
        """
        self.ensure_client_loaded(client_id)
        # Register the ticker with your AI universe (you can remove this if not wanted)
        self.AImanage.Client_add_stock_to_list(self.AImanage.client, ticker)
        # Record the trade in memory
        self.add_trade(client_id, ticker, market, side, qty, price, trade_time)
        # Persist (recompute positions + write workbook)
        if autosave:
            self.save_client_excel(client_id)

    # ---------- FIFO & PnL ----------
    def _fifo_match(self, client_id: str, ticker: str) -> Dict[str, Any]:
        """
        Internal: FIFO match SELLs to prior BUY lots to compute realized PnL.

        Returns:
            {
                "open_lots": [ {qty, price, time, market}, ... ]  # remaining BUY lots
                "realized":  DataFrame of realized rows for this (client, ticker)
            }

        Raises:
            ValueError if a SELL exceeds available BUY quantity (shorts not allowed here).
        """
        df = self.trades[(self.trades.client_id == client_id) & (self.trades.ticker == ticker)].copy()
        df = df.sort_values("trade_time")

        open_lots: List[Dict[str, Any]] = []
        realized_rows: List[Dict[str, Any]] = []

        for _, tr in df.iterrows():
            if tr.side == "BUY":
                open_lots.append({"qty": tr.qty, "price": tr.price, "time": tr.trade_time, "market": tr.market})
            else:  # SELL
                qty_to_match = tr.qty
                proceeds = tr.qty * tr.price
                matched_cost = 0.0
                sold_qty_total = 0.0

                # Consume from the oldest open BUY lots
                while qty_to_match > 1e-12 and open_lots:
                    lot = open_lots[0]
                    take = min(qty_to_match, lot["qty"])
                    matched_cost += take * lot["price"]
                    sold_qty_total += take
                    lot["qty"] -= take
                    qty_to_match -= take
                    if lot["qty"] <= 1e-12:
                        open_lots.pop(0)

                if qty_to_match > 1e-12:
                    # You tried to sell more than you own (no shorting allowed in this model)
                    raise ValueError(f"SELL exceeds available FIFO buys for {ticker} (client {client_id}).")

                realized_rows.append({
                    "client_id": client_id,
                    "ticker": ticker,
                    "market": tr.market,
                    "trade_time": tr.trade_time,
                    "qty_sold": sold_qty_total,
                    "proceeds": proceeds,
                    "cost": matched_cost,
                    "realized_pnl": proceeds - matched_cost
                })

        realized_df = (pd.DataFrame(realized_rows) if realized_rows else
                       pd.DataFrame(columns=["client_id","ticker","market","trade_time","qty_sold","proceeds","cost","realized_pnl"]))
        return {"open_lots": open_lots, "realized": realized_df}

    def compute_positions(self, client_id: Optional[str] = None) -> pd.DataFrame:
        """
        Rebuild realized PnL and compute current open positions with market values.

        Steps per (client_id, ticker):
            - FIFO-match to populate self.realized_ledger
            - Aggregate remaining lots -> qty, avg_cost, cost_basis
            - Fetch last price via yfinance -> market_value
            - Compute unrealized_pnl

        Returns:
            Positions DataFrame with columns:
                client_id, ticker, market, qty, avg_cost, cost_basis,
                last_price, market_value, unrealized_pnl

        Notes:
            - If client_id is None, computes for all clients (and fills realized_ledger for all).
            - This function reaches out to Yahoo; consider rate limiting for large universes.
        """
        # Load prior saved trades (no-op if workbook missing)
        self.ensure_client_loaded(client_id)

        df = self.trades.copy()
        if client_id is not None:
            df = df[df.client_id == client_id]

        positions: List[Dict[str, Any]] = []
        # Reset realized ledger and rebuild from scratch deterministically
        self.realized_ledger = pd.DataFrame(columns=self.realized_ledger.columns)

        if df.empty:
            return pd.DataFrame(columns=[
                "client_id","ticker","market","qty","avg_cost","cost_basis",
                "last_price","market_value","unrealized_pnl"
            ])

        for (cid, tkr), _ in df.groupby(["client_id", "ticker"]):
            fifo = self._fifo_match(cid, tkr)

            # Append realized rows for this ticker
            if not fifo["realized"].empty:
                if self.realized_ledger.empty:
                    self.realized_ledger = fifo["realized"].copy()
                else:
                    self.realized_ledger = pd.concat([self.realized_ledger, fifo["realized"]], ignore_index=True)

            # Aggregate remaining open lots
            lots = fifo["open_lots"]
            qty = float(sum(l["qty"] for l in lots)) if lots else 0.0
            if qty > 0:
                total_cost = float(sum(l["qty"] * l["price"] for l in lots))
                avg_cost = total_cost / qty
            else:
                total_cost = 0.0
                avg_cost = 0.0

            # Price & market value (None -> 0 MV)
            last_px = latest_close_yf(tkr)
            mkt_val = qty * last_px if (last_px is not None and qty > 0) else 0.0
            unreal = mkt_val - total_cost

            # Take latest market label for this ticker
            market_val = df[(df.client_id == cid) & (df.ticker == tkr)].market.iloc[-1]

            positions.append({
                "client_id": cid,
                "ticker": tkr,
                "market": market_val,
                "qty": qty,
                "avg_cost": round(avg_cost, 6),
                "cost_basis": round(total_cost, 2),
                "last_price": None if last_px is None else round(float(last_px), 6),
                "market_value": round(mkt_val, 2),
                "unrealized_pnl": round(unreal, 2)
            })

        pos_df = pd.DataFrame(positions)
        if not pos_df.empty:
            pos_df = pos_df.sort_values(["client_id","ticker"]).reset_index(drop=True)
        return pos_df

    def realized_pnl(self, client_id: Optional[str] = None) -> pd.DataFrame:
        """
        Return the realized PnL ledger (rebuilt by the latest compute_positions()).
        If client_id is provided, filter the ledger to that client.
        """
        df = self.realized_ledger.copy()
        if client_id is not None:
            df = df[df.client_id == client_id].reset_index(drop=True)
        return df

    # ---------- Client views ----------
    def get_client_holdings(self, client_id: str) -> pd.DataFrame:
        """
        Convenience: compute positions for the client and return only open positions (qty > 0).
        """
        pos = self.compute_positions(client_id=client_id)
        if pos.empty:
            return pos
        return pos[pos["qty"] > 0].reset_index(drop=True)

    def get_client_universe(self, client_id: str) -> List[str]:
        """
        List all tickers the client has ever traded (based on self.trades).
        """
        df = self.trades[self.trades.client_id == client_id]
        return sorted(df["ticker"].unique().tolist())

    def get_client_trades(self, client_id: str, ticker: Optional[str] = None) -> pd.DataFrame:
        """
        All trades for a client, optionally filtered by ticker (normalized for that client's market).
        Sorted ascending by trade_time.
        """
        df = self.trades[self.trades.client_id == client_id].copy()
        if ticker:
            df = df[df["ticker"] == normalize_ticker(ticker, df["market"].iloc[0] if not df.empty else "US")]
        return df.sort_values("trade_time").reset_index(drop=True)

    def client_portfolio_snapshot(self, client_id: str) -> Dict[str, Any]:
        """
        Build a one-shot snapshot dict:
            {
              "holdings_df": <open positions>,
              "realized_df": <realized PnL ledger for client>,
              "totals": {
                 "total_cost_basis",
                 "total_market_value",
                 "total_unrealized_pnl"
              }
            }
        Also prints the dict (you may want to remove the print in production).
        """
        holdings = self.get_client_holdings(client_id)
        realized = self.realized_pnl(client_id)

        totals = {
            "total_cost_basis": float(holdings["cost_basis"].sum()) if not holdings.empty else 0.0,
            "total_market_value": float(holdings["market_value"].sum()) if not holdings.empty else 0.0,
        }
        totals["total_unrealized_pnl"] = totals["total_market_value"] - totals["total_cost_basis"]
        print({"holdings_df": holdings, "realized_df": realized, "totals": totals})
        return {"holdings_df": holdings, "realized_df": realized, "totals": totals}

    # ---------- Save / Load one client's Excel ----------
    def save_client_excel(self, client_id: str, path: Optional[str] = None):
        """
        Overwrite a client's workbook with fresh Trades, Holdings, RealizedPnL, and Totals.
        Side-effect: calls client_portfolio_snapshot() which recomputes positions and realized ledger.
        """
        snap = self.client_portfolio_snapshot(client_id)  # recompute fresh
        path = path or self._client_path(client_id)

        with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
            self.get_client_trades(client_id).to_excel(xw, sheet_name="Trades", index=False)
            snap["holdings_df"].to_excel(xw, sheet_name="Holdings", index=False)
            snap["realized_df"].to_excel(xw, sheet_name="RealizedPnL", index=False)
            pd.DataFrame([snap["totals"]]).to_excel(xw, sheet_name="Totals", index=False)

    # ---------- Pretty print ----------
    def pretty_portfolio_print(self, client_id: str):
        """
        Console report for a client:
         - Open positions
         - Realized PnL
         - Trade history
         - Totals
        """
        holdings = self.get_client_holdings(client_id)
        realized  = self.realized_pnl(client_id)
        trades    = self.get_client_trades(client_id)
        snap      = self.client_portfolio_snapshot(client_id)

        print("\n================= CLIENT PORTFOLIO =================")
        print(f"Client: {client_id}")

        print("\n--- HOLDINGS (Open Positions) ---")
        if holdings.empty:
            print("(none)")
        else:
            cols = ["ticker","market","qty","avg_cost","cost_basis","last_price","market_value","unrealized_pnl"]
            print(holdings[cols].to_string(index=False))

        print("\n--- REALIZED PnL (Closed) ---")
        if realized.empty:
            print("(none)")
        else:
            cols = ["ticker","trade_time","qty_sold","proceeds","cost","realized_pnl"]
            realized_sorted = realized.sort_values("trade_time", ascending=False).reset_index(drop=True)
            print(realized_sorted[cols].to_string(index=False))

        print("\n--- TRADE HISTORY ---")
        if trades.empty:
            print("(none)")
        else:
            cols = ["trade_time","ticker","market","side","qty","price"]
            print(trades[cols].sort_values("trade_time").to_string(index=False))

        totals = snap["totals"]
        print("\n--- TOTALS ---")
        print(f"Total Cost Basis     : {totals['total_cost_basis']:.2f}")
        print(f"Total Market Value   : {totals['total_market_value']:.2f}")
        print(f"Total Unrealized PnL : {totals['total_unrealized_pnl']:.2f}")
        print("====================================================\n")
