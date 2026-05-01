# IDX AI Hedge Fund

An AI system that simulates a small hedge fund team — not one model predicting a stock, but multiple specialized agents that analyze, debate, and decide together.

🌐 **Dashboard:** [yazqe.github.io/idx-ai-hedge-fund/analysis](https://yazqe.github.io/idx-ai-hedge-fund/analysis/)

---

## The Idea

Most AI trading tools ask one model: *"Should I buy this?"*

This system works differently. For every stock, it runs:

1. **Four analysts** working in parallel — fundamentals, technical, sentiment, macro
2. **A bull and bear debate** — adversarial researchers argue for and against
3. **A trader** who proposes an entry, size, and timing
4. **Risk management** that can veto the trade
5. **A portfolio manager** who gives the final decision

Every stage writes in plain English. Every decision is traceable.

---

## Agents

**Analyst Layer** *(run in parallel)*

| | Agent | Focuses on |
|---|---|---|
| 📊 | [Fundamental](https://www.investopedia.com/terms/f/fundamentalanalysis.asp "Evaluates a company's intrinsic value using financial statements, ratios, earnings, and growth metrics to determine if a stock is under or overvalued.") | Valuation, earnings quality, balance sheet |
| 📉 | [Technical](https://www.investopedia.com/terms/t/technicalanalysis.asp "Studies price charts and indicators like RSI, MACD, and moving averages to identify patterns and predict future price movement based on historical data.") | RSI, MACD, SMA, momentum signals |
| 💬 | [Sentiment](https://www.investopedia.com/terms/m/marketsentiment.asp "Measures the overall attitude of investors toward a stock or market — bullish (optimistic) or bearish (pessimistic) — using news, social media, and crowd behavior.") | Market mood, crowd positioning |
| 📰 | [Macro](https://www.investopedia.com/terms/m/macroeconomics.asp "Analyzes broad economic factors — interest rates, inflation, GDP, currency strength, and geopolitical events — that influence the overall market and specific sectors.") | Sector rotation, BI rate, global events |

**Decision Layer** *(sequential)*

| | Agent | Role |
|---|---|---|
| 🐂🐻 | [Debate](https://www.investopedia.com/terms/b/bull.asp "Two researchers argue opposing sides — Bull (bullish case for buying) vs Bear (bearish case against) — for N configurable rounds, using analyst reports as evidence.") | Bull vs Bear argue N rounds using analyst evidence |
| 👨‍💼 | [Trader](https://www.investopedia.com/terms/t/trader.asp "Reads all analyst reports and the debate transcript, then proposes a concrete trade: direction (buy/sell), entry price, target, stop-loss, and position size.") | Converts debate into a trade proposal |
| ⚠️ | [Risk Manager](https://www.investopedia.com/terms/r/riskmanagement.asp "Acts as a gatekeeper — evaluates whether the proposed trade is safe given current volatility, liquidity, and portfolio exposure. Can veto the trade.") | Validates exposure, volatility, position size |
| 👔 | [Portfolio Manager](https://www.investopedia.com/terms/p/portfoliomanager.asp "The final authority. Reads everything — analyst reports, debate, trade proposal, and risk review — then issues a written decision: EXECUTE, MONITOR, or PASS.") | Final approval — **EXECUTE / MONITOR / PASS** |

---

## Output

Each stock analysis produces:

- Signal from each analyst with confidence score
- Debate summary — who won and why
- Trade parameters — entry, target, stop-loss, position size
- Risk flags from risk management
- Written reasoning from the portfolio manager

---

## Stock Selection

The daily batch screens IDX stocks across three criteria:

- **Top Value** — highest trading value (institutional activity)
- **Top Gainers** — strongest movers today
- **Top Frequency** — cross-list intersection score

Stocks appearing in multiple lists get priority.

---

## Setup

```bash
git clone https://github.com/yazqe/idx-ai-hedge-fund
cd idx-ai-hedge-fund
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Add to `.env`:
```
ANTHROPIC_API_KEY=your_key
SECRET_TOKEN=your_datasectors_key
```

Run:
```bash
python batch_analysis.py        # analyze top IDX stocks
python batch_analysis.py BBCA   # analyze one ticker
python api_server.py            # start local API for dashboard
```

---

## Data Sources

| Data | Source |
|---|---|
| Price, OHLCV, Foreign Flow | datasectors.com (IDX-native) |
| Fundamentals | Yahoo Finance |
| Stock screening | TradingView Scanner |

---

*Built with [LangGraph](https://github.com/langchain-ai/langgraph) + [Claude](https://anthropic.com). Not financial advice.*
