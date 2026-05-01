# IDX AI Hedge Fund

> **The system behaves like a small hedge fund team.**
> Instead of asking one AI model "should I buy this stock?", it runs a full organizational simulation — specialists analyze, researchers debate, a trader proposes, risk evaluates, and a portfolio manager gives final approval.

This is not _"AI predicts stock movement."_ It is closer to:

**AI organization simulation for trading decisions.**

Built for Indonesia Stock Exchange (IDX) using [LangGraph](https://github.com/langchain-ai/langgraph) + [Claude](https://anthropic.com).

🌐 **Live Dashboard:** [yazqe.github.io/idx-ai-hedge-fund/analysis](https://yazqe.github.io/idx-ai-hedge-fund/analysis/)

---

## How It Works

For every ticker, the system runs this pipeline:

```
1. Fetch market data (price, OHLCV, fundamentals, foreign flow)
        ↓
2. Four analyst agents run IN PARALLEL
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
   │ Fundamental  │  Technical   │  Sentiment   │    Macro     │
   └──────────────┴──────────────┴──────────────┴──────────────┘
        ↓
3. Bull vs Bear debate (N configurable rounds)
   🐂 Bullish Researcher  ←→  🐻 Bearish Researcher
        ↓
4. Trader proposes a trade (timing, direction, position size)
        ↓
5. Risk Management evaluates (volatility, liquidity, exposure)
        ↓
6. Portfolio Manager gives final approval or rejection
        ↓
7. Decision logged to Markdown + reflection injected into next run
```

Every stage produces **interpretable plain-English text** — fully auditable from analyst report to final decision.

---

## The Agents

### Analyst Layer — runs in parallel

| Agent | What it answers | Key outputs |
|---|---|---|
| **📊 Fundamental** | Is the company financially strong? Valuation fair? | PE, PB, ROE, revenue growth, debt, intrinsic value estimate |
| **📉 Technical** | Is momentum strong? Overbought or oversold? | RSI, MACD, SMA50/200, Bollinger, breakout/reversal signals |
| **💬 Sentiment** | Is the crowd bullish or bearish? Hype or panic? | Sentiment score, mood interpretation, short-term signal |
| **📰 Macro** | Did recent events change the outlook? | Sector rotation, BI rate impact, global macro risks |

> All four run in parallel. Each produces a structured `AnalystReport` with signal, confidence, key points, and risks.

### Debate Layer

| Agent | Role |
|---|---|
| **🐂 Bullish Researcher** | Argues why the stock should be bought, citing analyst evidence |
| **🐻 Bearish Researcher** | Argues why the stock should not be bought, challenging the bull case |

Debate runs for a **configurable number of rounds**. Strong disagreement = hidden risk signal. Quick consensus = higher conviction.

### Decision Layer

| Agent | Role | Output |
|---|---|---|
| **👨‍💼 Trader** | Converts debate into action — timing, direction, position size | `TradeProposal` |
| **⚠️ Risk Manager** | Validates: too volatile? illiquid? position too large? | `RiskReview` (APPROVE / REJECT) |
| **👔 Portfolio Manager** | Final authority — reads everything, decides, explains in writing | `FinalDecision` (EXECUTE / MONITOR / PASS) |

---

## Why This Architecture Matters

Traditional trading systems are often:
- Rule-based (if RSI < 30, buy)
- Black-box ML models (input price → output prediction)

This system is different:

| Property | This system |
|---|---|
| **Transparent** | Every agent writes readable English |
| **Traceable** | You can inspect what each analyst said, why the trader proposed an action, why risk approved or rejected |
| **Auditable** | Full decision log from market data to final call |
| **Adversarial** | Bull and bear actively try to find flaws in each other's argument |
| **Separated concerns** | "Good idea" (analyst + debate) vs "Safe trade" (risk layer) are distinct |

---

## Data Sources

| Data | Source |
|---|---|
| Price, OHLCV, Foreign Flow, Frequency | [datasectors.com](https://datasectors.com) (IDX-native) |
| Fundamentals (PE, PB, ROE, market cap) | Yahoo Finance |
| Candidate stocks | TradingView Scanner (top value + gainers + frequency) |

The system uses **three stock selection methods** for batch analysis:

- 💰 **Top Value** — most liquid by trading value (institutional focus)
- 📈 **Top Gainers** — strongest % movers today
- 🔄 **Top Frequency** — cross-list intersection score (volume + value + gainers)

---

## Output — Final Decision

```
EXECUTE  → Trade approved, entry/target/stop-loss defined
MONITOR  → Interesting but not ready — watch for confirmation
PASS     → Risk rejected or insufficient signal — do not trade
```

Every decision includes:
- Analyst signals with confidence scores
- Bull vs bear debate summary
- Risk level and flags
- Portfolio manager written reasoning

---

## System Architecture

```
User Input (ticker)
       ↓
 fetch_data ──── datasectors API (OHLCV + foreign flow)
                 Yahoo Finance (fundamentals)
       ↓
 load_memory ─── inject past trade reflections into context
       ↓
 run_analysts ── [Fundamental] [Technical] [Sentiment] [Macro] (parallel)
       ↓
 debate ───────── Bull ←→ Bear (N rounds)
       ↓
 trader ───────── timing · direction · position size
       ↓
 risk ─────────── volatility · liquidity · exposure check
       ↓
 portfolio_manager → EXECUTE / MONITOR / PASS + explanation
       ↓
 log ──────────── Markdown decision log + reflection for next run
```

Built on **LangGraph** `StateGraph` with SQLite checkpointing — crash-safe, resumable mid-run.

---

## Practical Notes

**Token cost:** One ticker run triggers 7–9 LLM calls (4 analysts + debate rounds + trader + risk + PM). Costs scale with debate rounds.

**Not financial advice.** This is a research framework demonstrating multi-agent AI orchestration. It is not intended for live automated trading without human oversight.

**Backtesting orientation.** The memory/reflection system compares past decisions against realized returns, but live broker integration requires additional wiring.

---

## Setup

```bash
git clone https://github.com/yazqe/idx-ai-hedge-fund
cd idx-ai-hedge-fund
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY and SECRET_TOKEN
```

## Usage

```bash
# Batch analysis — top IDX stocks by value + gainers + frequency
python batch_analysis.py

# Analyze a specific ticker
python batch_analysis.py BBCA

# Local API server (for Analyze Ticker tab in dashboard)
python api_server.py
# → open https://127.0.0.1:8765/
```

## Structured Schemas

All agent outputs use Pydantic schemas — no free-form JSON parsing:

```
AnalystReport   signal · confidence · key_points · risks · price_target
DebateResult    rounds · winner · consensus · confidence · summary
TradeProposal   action · entry_price · target · stop_loss · position_size
RiskReview      approved · risk_level · risk_flags · adjustments
FinalDecision   decision · entry · target · stop · position_size_pct · reasoning
```

---

*Inspired by the TradingAgents open-source framework. IDX-adapted with local data sources, multi-category stock screening, and a public dashboard.*
