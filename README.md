# Brokai — Task Breakdown & Status

> Purpose: Break down the work into smaller executable units, attach success criteria (DoD), dependencies, and priority, and prepare a roadmap for upcoming sprints.

---

## ✅ Completed

| ID | Area | Deliverable | Key Work | DoD (Definition of Done) | Artifacts |
|---|---|---|---|---|---|
| C1 | Analysis | Valuation of a private investment portfolio based on financial reports and up-to-date news | Report collection, DCF/multiples, news integration | Analytical reports + valuation output | - |
| C2 | Stock Scoring | Assigning a score to a stock based on 3-year history & performance | Historical features, normalization, scoring | Stable scoring module/file | - |
| C3 | Forecasting | Future valuation for a stock (reports + news) | Feature pipeline + baseline model | Run forecast for stock at given cut-off date | - |
| C4 | Recommendations | Recommended stocks | Score/forecast filtering, threshold setup | Top-N recommendations with short rationale | - |

---

## 📋 Backlog (To Do) — by Streams

### A. Data & Integrations (Market/News/Crypto)

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| D1 | Select real-time market data provider | Map providers (Polygon/IEX/Alpaca/IB/Bursa IL), check SLA & cost | Comparison table + written decision | - | High |
| D2 | Integrate Market Data (US) | Connect API, retry logic, throttling, caching | Internal endpoint returning OHLCV/Level-1 | D1 | High |
| D3 | Integrate Market Data (IL) | Connect TASE/broker, ticker mapping | Internal endpoint for IL data + delay validation | D1 | High |
| D4 | General News + Breaking | Choose aggregator, filter by ticker/lang | Unified feed with metadata & deduplication | D1 | High |
| D5 | Stock-specific News | NER/ticker matching, dedup, basic sentiment | API returns per-ticker news with sentiment | D4 | High |
| D6 | Crypto Integration | Provider (Binance/Coinbase), time conversions | Endpoint with OHLCV for top coins | D1 | Medium |
| D7 | Data Storage | Design DB schema (time-series, news, crypto) | Approved tables + retention policy | D2-D6 | High |

### B. News, Social & Influencers

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| N1 | Twitter/X Integration | API/alternative, text+metadata ingestion | Scheduled ingestion, storage, normalization | D7 | High |
| N2 | Instagram/Threads Integration | Legal/ethical access, provider integration | Data per creator/hashtag available | D7 | Medium |
| N3 | Influencer Discovery | Build seed list, rank by engagement/PageRank | Table of influencers with scores | N1-N2 | Medium |
| N4 | Text-to-Market Impact | Model linkage tweet/post ↔ return/vol | Correlation/VAR/Granger + significance report | N1 | High |
| N5 | Breaking Alerts | Rules/ML for major event detection | Alert with ticker/reason/source | D4, N1 | High |

### C. Modeling & Forecasting

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| M1 | Feature Engineering | Technical (MA/RSI/ATR), fundamental, macro | Feature notebook + unit tests | D2-D7 | High |
| M2 | Text Sentiment Features | FinBERT/Llama-FT, aspect-based sentiment | Sentiment features with time window | D4, N1 | High |
| M3 | Short-term Forecast Model | XGBoost/LSTM/Transformer | Evaluation by AUC/IC/R² for T+1/T+5 | M1-M2 | High |
| M4 | Medium/Long-term Model | Prophet/State-Space/Transformer | Accuracy vs benchmarks (Naive/ARIMA) | M1-M3 | Medium |
| M5 | Uncertainty Estimation | Quantile/Ensemble/Dropout | Forecasts with confidence intervals | M3-M4 | High |
| M6 | Explainability | SHAP/ICE/Feature Attribution | Explanatory report per ticker + API | M3 | High |

### D. Backtesting, Simulation & Decisioning

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| B1 | Backtesting Engine | Simulated trades, fees, slippage | Run on history with metrics | M1-M3 | High |
| B2 | Performance Metrics | CAGR, Sharpe, Sortino, MaxDD, HitRate | Automated report + JSON results | B1 | High |
| B3 | Decision Methodology | Signal→Position sizing (Kelly/Vol-Target) | Configurable decision module | M3, B1 | High |
| B4 | Future Scenario Simulation | Macro/event impacts (rate, war), MC/bootstrapping | API with impact per ticker/portfolio | M4, B1 | Medium |
| B5 | Risk Management | Stops, VaR/ES, exposure limits | Enforced in backtest + real-time | B1-B3 | High |

### E. Product: Web, Demo, Portfolio

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| P1 | Basic Website (MVP) | Results page, stock details, Top 10 | Responsive demo (desktop/mobile) | APIs D2-D5, M3 | High |
| P2 | Demo Account | Signup, dummy data, limited scenarios | Demo user runs filters+recommendations | P1 | High |
| P3 | AI Portfolio Display | Portfolio page, trade history | Graphs + explanations (from M6) | P1, M6 | High |
