"""LangGraph StateGraph orchestration for the IDX AI Hedge Fund."""
import asyncio
from typing import TypedDict, Optional, Annotated
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from schemas import GraphState
from data.market_data import fetch_market_data
from agents.analysts import fundamental, technical, sentiment, macro
from agents.debate import run_debate
from agents.trader import propose
from agents.risk_manager import review
from agents.portfolio_manager import decide
from memory.logger import log_run, load_recent_memory, reflect
import progress_tracker as PT


# ── LangGraph needs a plain TypedDict for state ───────────────────────────────
class HedgeFundState(TypedDict):
    ticker:          str
    market_data:     Optional[dict]
    analyst_reports: list[dict]
    debate_result:   Optional[dict]
    trade_proposal:  Optional[dict]
    risk_review:     Optional[dict]
    final_decision:  Optional[dict]
    memory_context:  str
    error:           Optional[str]
    run_id:          str


# ── Node functions ─────────────────────────────────────────────────────────────

def node_fetch_data(state: HedgeFundState) -> HedgeFundState:
    PT.update(state["ticker"], "fetch_data")
    try:
        data = fetch_market_data(state["ticker"])
        return {**state, "market_data": data.model_dump()}
    except Exception as e:
        return {**state, "error": f"Data fetch failed: {e}"}


def node_load_memory(state: HedgeFundState) -> HedgeFundState:
    PT.update(state["ticker"], "memory")
    raw = load_recent_memory(state["ticker"])
    reflection = reflect(raw, state["ticker"]) if raw else ""
    return {**state, "memory_context": reflection}


def node_run_analysts(state: HedgeFundState) -> HedgeFundState:
    from schemas import MarketData
    from concurrent.futures import ThreadPoolExecutor, as_completed
    PT.update(state["ticker"], "analysts")
    if state.get("error") or not state.get("market_data"):
        return state
    data = MarketData(**state["market_data"])
    try:
        analysts = [fundamental.analyze, technical.analyze, sentiment.analyze, macro.analyze]
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(fn, data) for fn in analysts]
            reports = []
            for f in futures:
                try:
                    reports.append(f.result())
                except Exception as e:
                    print(f"  ⚠️ Analyst error (skipped): {e}")
        PT.update(state["ticker"], "analysts_done")
        return {**state, "analyst_reports": [r.model_dump() for r in reports]}
    except Exception as e:
        return {**state, "error": f"Analysts failed: {e}"}


def node_debate(state: HedgeFundState) -> HedgeFundState:
    from schemas import AnalystReport
    PT.update(state["ticker"], "debate")
    if state.get("error") or not state.get("analyst_reports"):
        return state
    reports = [AnalystReport(**r) for r in state["analyst_reports"]]
    try:
        result = run_debate(state["ticker"], reports, rounds=1)
        PT.update(state["ticker"], "debate_done")
        return {**state, "debate_result": result.model_dump()}
    except Exception as e:
        return {**state, "error": f"Debate failed: {e}"}


def node_trader(state: HedgeFundState) -> HedgeFundState:
    from schemas import MarketData, AnalystReport, DebateResult
    PT.update(state["ticker"], "trader")
    if not state.get("market_data") or not state.get("analyst_reports") or not state.get("debate_result"):
        return {**state, "error": "Trader: missing market_data, analyst_reports, or debate_result"}
    data    = MarketData(**state["market_data"])
    reports = [AnalystReport(**r) for r in state["analyst_reports"]]
    debate  = DebateResult(**state["debate_result"])
    try:
        proposal = propose(data, reports, debate)
        PT.update(state["ticker"], "trader_done")
        return {**state, "trade_proposal": proposal.model_dump()}
    except Exception as e:
        return {**state, "error": f"Trader failed: {e}"}


def node_risk(state: HedgeFundState) -> HedgeFundState:
    from schemas import MarketData, TradeProposal
    PT.update(state["ticker"], "risk")
    if state.get("error") or not state.get("trade_proposal") or not state.get("market_data"):
        return state
    data     = MarketData(**state["market_data"])
    proposal = TradeProposal(**state["trade_proposal"])
    try:
        risk = review(proposal, data)
        PT.update(state["ticker"], "risk_done")
        return {**state, "risk_review": risk.model_dump()}
    except Exception as e:
        return {**state, "error": f"Risk failed: {e}"}


def node_portfolio_manager(state: HedgeFundState) -> HedgeFundState:
    from schemas import TradeProposal, RiskReview
    PT.update(state["ticker"], "pm")
    if state.get("error") or not state.get("trade_proposal") or not state.get("risk_review"):
        return state
    proposal = TradeProposal(**state["trade_proposal"])
    risk     = RiskReview(**state["risk_review"])
    try:
        decision = decide(proposal, risk, memory_context=state["memory_context"])
        return {**state, "final_decision": decision.model_dump()}
    except Exception as e:
        return {**state, "error": f"PM failed: {e}"}


def node_log(state: HedgeFundState) -> HedgeFundState:
    from schemas import (MarketData, AnalystReport, DebateResult,
                         TradeProposal, RiskReview, FinalDecision)
    gs = GraphState(
        ticker=state["ticker"],
        market_data=MarketData(**state["market_data"]) if state.get("market_data") else None,
        analyst_reports=[AnalystReport(**r) for r in state.get("analyst_reports", [])],
        debate_result=DebateResult(**state["debate_result"]) if state.get("debate_result") else None,
        trade_proposal=TradeProposal(**state["trade_proposal"]) if state.get("trade_proposal") else None,
        risk_review=RiskReview(**state["risk_review"]) if state.get("risk_review") else None,
        final_decision=FinalDecision(**state["final_decision"]) if state.get("final_decision") else None,
        memory_context=state.get("memory_context", ""),
        run_id=state["run_id"],
    )
    log_path = log_run(gs)
    print(f"[LOG] Saved to {log_path}")
    PT.update(state["ticker"], "done")
    return state


# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    g = StateGraph(HedgeFundState)

    g.add_node("fetch_data",        node_fetch_data)
    g.add_node("load_memory",       node_load_memory)
    g.add_node("run_analysts",      node_run_analysts)
    g.add_node("debate",            node_debate)
    g.add_node("trader",            node_trader)
    g.add_node("risk",              node_risk)
    g.add_node("portfolio_manager", node_portfolio_manager)
    g.add_node("log",               node_log)

    g.set_entry_point("fetch_data")
    g.add_edge("fetch_data",        "load_memory")
    g.add_edge("load_memory",       "run_analysts")
    g.add_edge("run_analysts",      "debate")
    g.add_edge("debate",            "trader")
    g.add_edge("trader",            "risk")
    g.add_edge("risk",              "portfolio_manager")
    g.add_edge("portfolio_manager", "log")
    g.add_edge("log",               END)

    return g.compile(checkpointer=checkpointer)
