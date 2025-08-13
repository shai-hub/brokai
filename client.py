# client_portfolio.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from brokai.StockManagement import StockManagement
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import os
import random
import string
import os

# ---------- Helpers ----------
def normalize_ticker(ticker: str, market: str) -> str:
    t = str(ticker).strip().upper()
    m = str(market).strip().upper()
    # Yahoo symbol for TASE requires .TA suffix
    if m == "IL" and not t.endswith(".TA"):
        t += ".TA"
    return t

def latest_close_yf(ticker: str) -> Optional[float]:
    """
    Get most recent available price from Yahoo (delayed).
    Try 1-minute intraday; fallback to last daily close.
    """
    try:
        tk = yf.Ticker(ticker)
        intraday = tk.history(period="1d", interval="1m")
        if isinstance(intraday, pd.DataFrame) and not intraday.empty:
            val = intraday["Close"].dropna()
            if not val.empty:
                return float(val.iloc[-1])
        daily = tk.history(period="5d", interval="1d")
        if isinstance(daily, pd.DataFrame) and not daily.empty:
            val = daily["Close"].dropna()
            if not val.empty:
                return float(val.iloc[-1])
    except Exception:
        pass
    return None


# ---------- Data model ----------
@dataclass
class Trade:
    client_id: str
    ticker: str          # normalized (e.g., AAPL or ILCO.TA)
    market: str          # "US" or "IL"
    side: str            # "BUY" or "SELL"
    qty: float           # positive quantities
    price: float         # per-share trade price
    trade_time: datetime

# ---------- Portfolio ----------
class NewModelClientPortfolio:
    """
    - Store trades in a DataFrame
    - Compute positions with FIFO
    - Compute realized/unrealized P&L (using delayed Yahoo prices)
    - One Excel per client (auto-load & auto-save)
    """

    def __init__(self, StockManagement):
        self.trades = pd.DataFrame(columns=[
            "client_id","ticker","market","side","qty","price","trade_time"
        ])
        self.realized_ledger = pd.DataFrame(columns=[
            "client_id","ticker","market","trade_time","qty_sold","proceeds","cost","realized_pnl"
        ])
        self.AImanage= StockManagement

        # Folder for per-client files
        self.storage_dir = "clients_portfolios"
        os.makedirs(self.storage_dir, exist_ok=True)

    # ---------- Paths ----------
    def _client_path(self, client_id: str) -> str:
        safe_id = str(client_id).replace("/", "_").replace("\\", "_")
        return os.path.join(self.storage_dir, f"{safe_id}_portfolio.xlsx")

    # ---------- Load existing client workbook (if any) ----------
    def ensure_client_loaded(self, client_id: str):
        """
        If this client's workbook exists, load its Trades into self.trades
        (without duplicating rows). No-op if file doesn't exist.
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
        Adds a new buy/sell into self.trades (no file I/O).
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
        # Avoid concat warning by using .loc append
        self.trades.loc[len(self.trades)] = row

    # Helper that also auto-loads & auto-saves for a given client
    def add_trade_for_client(self, client_id: str, ticker: str, market: str,
                             side: str, qty: float, price: float,
                             trade_time: Optional[datetime] = None,
                             autosave: bool = True):
        self.ensure_client_loaded(client_id)
        self.AImanage.Client_add_stock_to_list(self.AImanage.client, ticker)
        self.add_trade(client_id, ticker, market, side, qty, price, trade_time)
        if autosave:
            self.save_client_excel(client_id)

    # ---------- FIFO & PnL ----------
    def _fifo_match(self, client_id: str, ticker: str) -> Dict[str, Any]:
        """
        Build FIFO lots and compute realized PnL for sells, returning:
          - open_lots: list of remaining BUY lots after matching sells
          - realized: DataFrame of realized PnL rows (for this client/ticker)
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
        Calculates positions & unrealized PnL (and rebuilds realized ledger).
        """
        self.ensure_client_loaded(client_id)

        df = self.trades.copy()
        if client_id is not None:
            df = df[df.client_id == client_id]

        positions: List[Dict[str, Any]] = []
        self.realized_ledger = pd.DataFrame(columns=self.realized_ledger.columns)  # rebuild fresh

        if df.empty:
            return pd.DataFrame(columns=[
                "client_id","ticker","market","qty","avg_cost","cost_basis",
                "last_price","market_value","unrealized_pnl"
            ])

        for (cid, tkr), _ in df.groupby(["client_id", "ticker"]):
            fifo = self._fifo_match(cid, tkr)

            # realized
            if not fifo["realized"].empty:
                if self.realized_ledger.empty:
                    self.realized_ledger = fifo["realized"].copy()
                else:
                    self.realized_ledger = pd.concat([self.realized_ledger, fifo["realized"]], ignore_index=True)

            # open lots -> qty/avg cost
            lots = fifo["open_lots"]
            qty = float(sum(l["qty"] for l in lots)) if lots else 0.0
            if qty > 0:
                total_cost = float(sum(l["qty"] * l["price"] for l in lots))
                avg_cost = total_cost / qty
            else:
                total_cost = 0.0
                avg_cost = 0.0

            # price & MV
            last_px = latest_close_yf(tkr)
            mkt_val = qty * last_px if (last_px is not None and qty > 0) else 0.0
            unreal = mkt_val - total_cost

            # market label
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
        Returns the realized P&L ledger (built during compute_positions()).
        """
        df = self.realized_ledger.copy()
        if client_id is not None:
            df = df[df.client_id == client_id].reset_index(drop=True)
        return df

    # ---------- Client views ----------
    def get_client_holdings(self, client_id: str) -> pd.DataFrame:
        pos = self.compute_positions(client_id=client_id)
        if pos.empty:
            return pos
        return pos[pos["qty"] > 0].reset_index(drop=True)

    def get_client_universe(self, client_id: str) -> List[str]:
        df = self.trades[self.trades.client_id == client_id]
        return sorted(df["ticker"].unique().tolist())

    def get_client_trades(self, client_id: str, ticker: Optional[str] = None) -> pd.DataFrame:
        df = self.trades[self.trades.client_id == client_id].copy()
        if ticker:
            df = df[df["ticker"] == normalize_ticker(ticker, df["market"].iloc[0] if not df.empty else "US")]
        return df.sort_values("trade_time").reset_index(drop=True)

    def client_portfolio_snapshot(self, client_id: str) -> Dict[str, Any]:
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
        # Recompute prices and ledger
        snap = self.client_portfolio_snapshot(client_id)
        path = path or self._client_path(client_id)

        with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
            self.get_client_trades(client_id).to_excel(xw, sheet_name="Trades", index=False)
            snap["holdings_df"].to_excel(xw, sheet_name="Holdings", index=False)
            snap["realized_df"].to_excel(xw, sheet_name="RealizedPnL", index=False)
            pd.DataFrame([snap["totals"]]).to_excel(xw, sheet_name="Totals", index=False)

    
    # ---------- Pretty print ----------
    def pretty_portfolio_print(self, client_id: str):
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
