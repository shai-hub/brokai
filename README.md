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

| ID | Task | Sub-steps | DoD | Dependencies | Priority |Done by
|---|---|---|---|---|---|---|
| D1 | Select real-time market data provider | Map providers (Polygon/IEX/Alpaca/IB/Bursa IL), check SLA & cost | Comparison table + written decision | - | High |
| D2 | Integrate Market Data (US) | Connect API, retry logic, throttling, caching | Internal endpoint returning OHLCV/Level-1 | D1 | High |
| D3 | Integrate Market Data (IL) | Connect TASE/broker, ticker mapping | Internal endpoint for IL data + delay validation | D1 | High |
| D4 | General News + Breaking | Choose aggregator, filter by ticker/lang | Unified feed with metadata & deduplication | D1 | High |
| D5 | Stock-specific News | NER/ticker matching, dedup, basic sentiment | API returns per-ticker news with sentiment | D4 | High |
| D6 | Crypto Integration | Provider (Binance/Coinbase), time conversions | Endpoint with OHLCV for top coins | D1 | Medium |
| D7 | Data Storage | Design DB schema (time-series, news, crypto) | Approved tables + retention policy | D2-D6 | High |

### B. News, Social & Influencers

| ID | Task | Sub-steps | DoD | Dependencies | Priority | Do |
|---|---|---|---|---|---|---|
| N1 | Twitter/X Integration | API/alternative, text+metadata ingestion | Scheduled ingestion, storage, normalization | D7 | High | Ido |
| N2 | Instagram/Threads Integration | Legal/ethical access, provider integration | Data per creator/hashtag available | D7 | Medium | - |
| N3 | Influencer Discovery | Build seed list, rank by engagement/PageRank | Table of influencers with scores | N1-N2 | Medium | - |
| N4 | Text-to-Market Impact | Model linkage tweet/post ↔ return/vol | Correlation/VAR/Granger + significance report | N1 | High | - |
| N5 | Breaking Alerts | Rules/ML for major event detection | Alert with ticker/reason/source | D4, N1 | High | - |

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

### F. Competitive Advantage & Differentiators

| ID | Task | Sub-steps | DoD | Dependencies | Priority |
|---|---|---|---|---|---|
| X1 | Full Transparency | Add visual explanations (graphs of sentiment vs price, sources, SHAP reports) | Each recommendation must include a “Why” panel | M6 | High |
| X2 | Future Simulation Engine | Build “what-if” scenarios (interest rate hike, war, inflation) | Users can run custom scenarios and see expected impact | B4 | High |
| X3 | Social-Driven Insights | Real-time influencer & sentiment correlation dashboards | Graph showing correlation between tweets/posts and stock moves | N4 | High |
| X4 | AI Portfolio Manager | AI-managed demo portfolio, compared to benchmarks (S&P500, TA-125) | Live demo portfolio with performance tracking | P3 | High |
| X5 | Risk Management Layer | Implement stops, VaR/ES, exposure rules in live + backtest | System prevents reckless trades | B5 | High |
| X6 | Demo Experience | Free demo with virtual portfolio | New users can try without risk | P2 | Medium |
| X7 | Dual Market Coverage | Support US + Israel equities + Crypto in one tool | Seamless cross-market analysis | D2, D3, D6 | High |
| X8 | Regulatory Compliance | Ensure GDPR, ESG, MiFID II alignment | Compliance docs & automated reports | D7 | Medium |


# Brokai — Project Roadmap & Team Breakdown

This README serves as the central roadmap for Brokai.  
Each section is owned by a dedicated team. For details, see the linked docs.

---

## ✅ Completed
- Portfolio valuation based on financial analysis & news
- Stock scoring (3-year history & performance)
- Future valuation (financial reports + news)
- Recommended stocks list

---

## 📋 Workstreams & Teams

### 1. Data & Integrations Team
**Scope**: Market data (US, IL), crypto, storage, compliance  
**Tasks**: D1–D7, X7, X8  
**Deliverables**: APIs for OHLCV, news feeds, crypto integration, DB schema  
📄 [docs/data_integrations.md](docs/data_integrations.md)

---

### 2. News & Social AI Team
**Scope**: Social feeds, influencers, sentiment, breaking events  
**Tasks**: N1–N5, X3  
**Deliverables**: Ingestion pipelines, influencer scoring, correlation dashboards  
📄 [docs/news_social.md](docs/news_social.md)

---

### 3. Modeling & Forecasting Team
**Scope**: Features, ML models, explainability, scenario modeling  
**Tasks**: M1–M6, X1, X2  
**Deliverables**: Forecast models, SHAP explainability, scenario simulations  
📄 [docs/modeling.md](docs/modeling.md)

---

### 4. Quant & Decisioning Team
**Scope**: Backtesting, KPIs, risk management, trading logic  
**Tasks**: B1–B5, X2, X5  
**Deliverables**: Backtesting engine, performance metrics, risk framework  
📄 [docs/quant_decision.md](docs/quant_decision.md)

---

### 5. Product & Frontend Team
**Scope**: Website MVP, demo account, portfolio UI  
**Tasks**: P1–P3, X4, X6  
**Deliverables**: Responsive website, demo user account, AI-managed portfolio view  
📄 [docs/product.md](docs/product.md)

---

### 6. BizDev & Strategy Team
**Scope**: Competitive positioning, GTM strategy, investor materials  
**Tasks**: X1–X8 (non-technical parts)  
**Deliverables**: Competitor matrix, go-to-market strategy, compliance docs  
📄 [docs/strategy.md](docs/strategy.md)

---

## 🔍 How to Track Progress
- Each team updates their doc under `/docs/` folder.  
- Use checkboxes `[ ]` / `[x]` for tasks in progress vs completed.  
- Weekly sync: update this README with high-level status.

---

## 📊 Next Steps
- [ ] Set up `/docs/` folder with team-specific markdown files  
- [ ] Assign team leads for each stream  
- [ ] Move backlog tasks into GitHub Projects or Jira for sprint planning
