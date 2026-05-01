"""All Pydantic schemas for the IDX AI Hedge Fund system."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class Signal(str, Enum):
    STRONG_BUY  = "STRONG_BUY"
    BUY         = "BUY"
    HOLD        = "HOLD"
    SELL        = "SELL"
    STRONG_SELL = "STRONG_SELL"

class Stance(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"

class RiskLevel(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"
    REJECT = "REJECT"


# ── Market Data ───────────────────────────────────────────────────────────────

class MarketData(BaseModel):
    ticker:        str
    price:         float
    change_pct:    float
    volume:        int
    avg_vol_10d:   Optional[int]   = None
    high_52w:      Optional[float] = None
    low_52w:       Optional[float] = None
    pe_ratio:      Optional[float] = None
    pb_ratio:      Optional[float] = None
    market_cap:    Optional[float] = None
    revenue_growth:Optional[float] = None
    roe:           Optional[float] = None
    debt_equity:   Optional[float] = None
    rsi_14:          Optional[float] = None
    macd:            Optional[float] = None
    macd_signal:     Optional[float] = None
    sma_50:          Optional[float] = None
    sma_200:         Optional[float] = None
    sector:          Optional[str]   = None
    foreign_flow_net:Optional[float] = None  # datasectors: net foreign flow (Rp)
    avg_frequency:   Optional[int]   = None  # datasectors: avg daily transactions
    fetched_at:      datetime        = Field(default_factory=datetime.now)


# ── Analyst Reports ───────────────────────────────────────────────────────────

class AnalystReport(BaseModel):
    analyst_type:  Literal["fundamental", "technical", "sentiment", "macro"]
    ticker:        str
    signal:        Signal
    confidence:    float = Field(ge=0.0, le=1.0, description="0.0–1.0")
    summary:       str   = Field(description="2-4 sentence analysis")
    key_points:    list[str] = Field(description="Top 3–5 supporting data points")
    risks:         list[str] = Field(description="Top 2–3 risks to this view")
    price_target:  Optional[float] = None
    created_at:    datetime = Field(default_factory=datetime.now)


# ── Debate ────────────────────────────────────────────────────────────────────

class DebateMessage(BaseModel):
    round:     int
    stance:    Stance
    argument:  str = Field(description="Argument for bull or bear case")
    evidence:  list[str] = Field(description="Specific data points cited")
    rebuttal:  Optional[str] = Field(None, description="Counter to previous argument")

class DebateResult(BaseModel):
    ticker:       str
    rounds:       list[DebateMessage]
    winner:       Optional[Stance]     = None
    consensus:    Signal
    confidence:   float = Field(ge=0.0, le=1.0)
    summary:      str


# ── Trade Proposal ────────────────────────────────────────────────────────────

class TradeProposal(BaseModel):
    ticker:          str
    action:          Signal
    quantity:        int   = Field(description="Number of shares")
    entry_price:     float
    target_price:    float
    stop_loss:       float
    hold_period:     str   = Field(description="e.g. '2 weeks', '1 month'")
    rationale:       str
    analyst_signals: list[Signal] = Field(description="Input signals from analysts")
    debate_outcome:  Signal
    created_at:      datetime = Field(default_factory=datetime.now)


# ── Risk Review ───────────────────────────────────────────────────────────────

class RiskReview(BaseModel):
    ticker:           str
    approved:         bool
    risk_level:       RiskLevel
    position_size_pct:float = Field(ge=0.0, le=100.0, description="% of portfolio")
    max_loss_pct:     float = Field(description="Max acceptable loss %")
    risk_flags:       list[str]
    adjustments:      Optional[str] = Field(None, description="Suggested adjustments if not fully approved")
    reviewed_at:      datetime = Field(default_factory=datetime.now)


# ── Final Decision ────────────────────────────────────────────────────────────

class FinalDecision(BaseModel):
    ticker:            str
    decision:          Literal["EXECUTE", "PASS", "MONITOR"]
    action:            Optional[Signal]  = None
    quantity:          Optional[int]     = None
    entry_price:       Optional[float]   = None
    target_price:      Optional[float]   = None
    stop_loss:         Optional[float]   = None
    position_size_pct: float = 0.0
    reasoning:         str
    portfolio_context: str = Field(description="How this fits current portfolio")
    decided_at:        datetime = Field(default_factory=datetime.now)


# ── LangGraph State ───────────────────────────────────────────────────────────

class GraphState(BaseModel):
    ticker:           str
    market_data:      Optional[MarketData]     = None
    analyst_reports:  list[AnalystReport]      = []
    debate_result:    Optional[DebateResult]   = None
    trade_proposal:   Optional[TradeProposal]  = None
    risk_review:      Optional[RiskReview]     = None
    final_decision:   Optional[FinalDecision]  = None
    error:            Optional[str]            = None
    memory_context:   str                      = ""
    run_id:           str                      = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
