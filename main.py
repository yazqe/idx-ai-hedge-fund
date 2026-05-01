"""IDX AI Hedge Fund — entry point."""
import sys
import json
from graph import run


def print_report(state: dict) -> None:
    print("\n" + "═"*60)
    print(f"  IDX AI HEDGE FUND — {state['ticker']}")
    print("═"*60)

    if state.get("error"):
        print(f"\n❌ Error: {state['error']}")
        return

    # Analyst signals
    print("\n📊 ANALYST SIGNALS:")
    for r in state.get("analyst_reports", []):
        print(f"  {r['analyst_type'].upper():<15} {r['signal']:<12} ({r['confidence']:.0%})")

    # Debate
    if d := state.get("debate_result"):
        print(f"\n⚔️  DEBATE: {d.get('winner','TIE')} wins | Consensus: {d['consensus']}")
        print(f"   {d['summary']}")

    # Trade proposal
    if p := state.get("trade_proposal"):
        print(f"\n📈 TRADE PROPOSAL:")
        print(f"  Action:  {p['action']}")
        print(f"  Entry:   Rp{p['entry_price']:,.0f}")
        print(f"  Target:  Rp{p['target_price']:,.0f}")
        print(f"  Stop:    Rp{p['stop_loss']:,.0f}")
        print(f"  Hold:    {p['hold_period']}")

    # Risk
    if r := state.get("risk_review"):
        print(f"\n🛡️  RISK REVIEW: {r['risk_level']} | Approved: {r['approved']}")
        if r.get("risk_flags"):
            for f in r["risk_flags"]:
                print(f"  ⚠️  {f}")

    # Final decision
    if fd := state.get("final_decision"):
        icon = {"EXECUTE": "✅", "PASS": "⛔", "MONITOR": "👀"}.get(fd["decision"], "❓")
        print(f"\n{icon} FINAL DECISION: {fd['decision']}")
        print(f"  {fd['reasoning']}")

    print("\n" + "═"*60 + "\n")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBCA"
    print(f"\n🤖 Running IDX AI Hedge Fund for {ticker}...\n")
    state = run(ticker)
    print_report(state)
