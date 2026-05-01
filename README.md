# IDX AI Hedge Fund

Multi-agent AI trading system for Indonesia Stock Exchange (IDX) built with LangGraph + Claude.

## Architecture

```
MarketData → [4 Analysts in parallel] → Debate → Trader → Risk → Portfolio Manager
                                                                    ↓
                                                             FinalDecision
                                                                    ↓
                                                           Memory Log + Reflection
```

## Agents

| Agent | Role | Output |
|-------|------|--------|
| **Fundamental** | Valuation, growth, quality | AnalystReport |
| **Technical** | RSI, MACD, SMA, momentum | AnalystReport |
| **Sentiment** | News, volume patterns | AnalystReport |
| **Macro** | IDX context, sector rotation | AnalystReport |
| **Debate** | Bull vs Bear, N rounds | DebateResult |
| **Trader** | Entry/exit proposal | TradeProposal |
| **Risk Manager** | Rules + LLM review | RiskReview |
| **Portfolio Manager** | Final decision | FinalDecision |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
# Analyze a single stock
python main.py BBCA

# Analyze any IDX stock
python main.py BUMI
python main.py TLKM
python main.py GOTO
```

## Features
- **4 analysts run in parallel** via asyncio
- **Configurable debate rounds** (default: 2)
- **SQLite checkpointing** via LangGraph
- **Memory & reflection** — learns from past runs
- **Pydantic schemas** — strict structured output throughout
