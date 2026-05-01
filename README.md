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
| 📊 | Fundamental | Valuation, earnings quality, balance sheet |
| 📉 | Technical | RSI, MACD, SMA, momentum signals |
| 💬 | Sentiment | Market mood, crowd positioning |
| 📰 | Macro | Sector rotation, BI rate, global events |

**Decision Layer** *(sequential)*

| | Agent | Role |
|---|---|---|
| 🐂🐻 | Debate | Bull vs Bear argue N rounds using analyst evidence |
| 👨‍💼 | Trader | Converts debate into a trade proposal |
| ⚠️ | Risk Manager | Validates exposure, volatility, position size |
| 👔 | Portfolio Manager | Final approval — **EXECUTE / MONITOR / PASS** |

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
