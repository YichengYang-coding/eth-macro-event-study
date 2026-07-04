"""
scripts/ladder_straddle_postmay_v0_5.py
=======================================

Custom full-position 50/50 straddle with a LADDER exit, post-May-2025 only.
Entry = anchor − 1 minute. 14 events: 7 CPI + 1 Jackson Hole + 6 FOMC.
FOMC run under TWO anchors (press-conf vs statement) for comparison.

Costs (per leg): entry 0.10% (0.05 fee + 0.05 slip) + exit 0.10% = 0.20% of leg
notional. Full position 50/50 -> total cost = 0.20% of capital per event.

Per-leg ladder (price treated as CONTINUOUS: threshold fills at the exact level
via 1m high/low; only "market" exits use the discrete minute price):

WINNING (favorable) side, measured from entry:
- reach 5.0% with no half sold yet  -> sell half @3.0% and half @5.0%
- reach 3.0% (not yet 5)             -> sell HALF @3.0%, start 3-min timer on the rest
    * rest reaches 5.0%              -> rest @5.0%
    * rest retraces to <=3.0%        -> rest @3.0%
    * 3-min timer ends in (3%,5%)    -> rest @market (that minute's price)
- never reached 3.0% -> wait 3 min from EVENT:
    * favorable went >2% then gives back to 2.0% -> all @2.0%
    * crosses 3.0% in window -> switch to ladder above
    * 3-min ends, still <3% -> all @market (signed; may be negative)
LOSING side: adverse reaches 1.0% -> that leg @ −1.0%.

Same-candle priority (documented modeling choice): hard −1% stop first, then the
favorable ladder (5 before 3), then retracement gives (2%/3% floor), then market
deadline. Remaining-half management begins the candle AFTER the half-sale.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "powell_v01", ROOT / "scripts" / "powell_eth_event_backtest_v0_1.py")
v01 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v01)

ENTRY_LEAD = 1          # buy 1 minute before anchor
COST_PER_LEG = 0.20     # % of leg notional (entry .10 + exit .10)
TP1, TP2, FLOOR, GIVEBACK, STOP = 3.0, 5.0, 3.0, 2.0, 1.0
WAIT = 3                # minutes

SOURCES = {
    "powell":  ("data/powell_eth_1m/ETHUSDT-1m-4days_with_utc.csv", "%Y/%m/%d %H:%M"),
    "cpi_ppi": ("data/cpi_ppi_eth_1m/ETHUSDT-1m-cpi_ppi_2025_with_utc.csv", None),
    "fomc":    ("data/fomc_eth_1m/ETHUSDT-1m-fomc_2025_with_utc.csv", None),
}

# post-May universe
CPI = [("2025-05-13 12:30", "CPI_Apr2025"), ("2025-06-11 12:30", "CPI_May2025"),
       ("2025-07-15 12:30", "CPI_Jun2025"), ("2025-08-12 12:30", "CPI_Jul2025"),
       ("2025-09-11 12:30", "CPI_Aug2025"), ("2025-10-24 12:30", "CPI_Sep2025_Delayed"),
       ("2025-12-18 13:30", "CPI_Nov2025_Delayed")]
JH = [("2025-08-22 14:00", "Powell_Jackson_Hole")]
FOMC_PRESS = [("2025-05-07 18:30", "FOMC_May"), ("2025-06-18 18:30", "FOMC_Jun"),
              ("2025-07-30 18:30", "FOMC_Jul"), ("2025-09-17 18:30", "FOMC_Sep"),
              ("2025-10-29 18:30", "FOMC_Oct"), ("2025-12-10 19:30", "FOMC_Dec")]


def load_all():
    fr = []
    for nm, (path, fmt) in SOURCES.items():
        d = pd.read_csv(ROOT / path, encoding="utf-8-sig")
        d["dt"] = (pd.to_datetime(d["open_time_utc"], format=fmt) if fmt
                   else pd.to_datetime(d["open_time_utc"])).dt.tz_localize("UTC")
        fr.append(d[["dt", "open", "high", "low", "close"]])
    return pd.concat(fr).drop_duplicates("dt").sort_values("dt").set_index("dt")


def simulate_leg(df, entry_ts, event_ts, side, max_min=130):
    """Return (gross_ret_pct_on_leg, reason) for one leg under the ladder rules."""
    e = v01.price_at(df, entry_ts, "open")
    span = df[(df.index >= entry_ts) & (df.index <= event_ts + timedelta(minutes=max_min))]
    if span.empty or np.isnan(e):
        return np.nan, "no_data"

    def metrics(c):
        # returns (fav_high, fav_close, adv_ext)  — all in %
        if side == "long":
            return (c["high"]/e-1)*100, (c["close"]/e-1)*100, (c["low"]/e-1)*100
        # short profits when price falls: favorable uses low/close, adverse uses high
        return (1-c["low"]/e)*100, (1-c["close"]/e)*100, (1-c["high"]/e)*100

    branchB_deadline = event_ts + timedelta(minutes=WAIT)
    remaining, realized = 1.0, 0.0
    half_sold, t_half, fav_peak = False, None, -1e9
    rows = list(span.iterrows())
    for i, (ts, c) in enumerate(rows):
        fav_high, fav_close, adv_ext = metrics(c)
        fav_peak = max(fav_peak, fav_high)            # breakout peak via highs

        # 1) hard stop on remaining (continuous touch via extreme)
        if adv_ext <= -STOP:
            realized += remaining*(-STOP); return realized, "stop_-1%"

        if not half_sold:
            if fav_high >= TP2:                        # passed through 3 then 5
                realized += 0.5*TP1 + 0.5*TP2; return realized, "tp_3_and_5_same_bar"
            if fav_high >= TP1:                        # sell half @3, manage rest
                realized += 0.5*TP1; remaining = 0.5
                half_sold, t_half = True, ts
                continue                               # manage remaining from next bar
            if fav_peak >= GIVEBACK and fav_close <= GIVEBACK:   # 2% giveback (close-confirmed)
                realized += remaining*GIVEBACK; return realized, "giveback_2%"
            if ts >= branchB_deadline:                 # 3-min market exit, never hit 3
                realized += remaining*fav_close; return realized, "market_event+3"
        else:
            if fav_high >= TP2:
                realized += remaining*TP2; return realized, "rest_@5%"
            if fav_close <= FLOOR:                     # retrace (close) to <=3
                realized += remaining*FLOOR; return realized, "rest_floor_@3%"
            if ts >= t_half + timedelta(minutes=WAIT):
                realized += remaining*fav_close; return realized, "rest_market_@t_half+3"

    last = rows[-1][1]; _, fav_close, _ = metrics(last)
    realized += remaining*fav_close
    return realized, "force_close_end"


def run_event(df, anchor_str, name, etype):
    anchor = pd.Timestamp(anchor_str, tz="UTC")
    entry = anchor - timedelta(minutes=ENTRY_LEAD)
    lg, lr = simulate_leg(df, entry, anchor, "long")
    sg, sr = simulate_leg(df, entry, anchor, "short")
    long_net, short_net = lg - COST_PER_LEG, sg - COST_PER_LEG
    port_gross = 0.5*(lg + sg)
    port_net = 0.5*(long_net + short_net)              # = port_gross - 0.20
    return {
        "event_name": name, "event_type": etype, "anchor_utc": anchor_str, "entry_utc": entry.strftime("%Y-%m-%d %H:%M"),
        "long_leg_gross_pct": round(lg, 4), "long_exit": lr,
        "short_leg_gross_pct": round(sg, 4), "short_exit": sr,
        "portfolio_gross_pct": round(port_gross, 4), "portfolio_net_pct": round(port_net, 4),
    }


def aggregate(rows, label):
    df = pd.DataFrame(rows).sort_values("anchor_utc").reset_index(drop=True)
    s = df["portfolio_net_pct"]
    eq, peak, dd = 1.0, 1.0, 0.0
    eqs = []
    for r in s:
        eq *= (1 + r/100.0); peak = max(peak, eq); dd = min(dd, eq/peak-1); eqs.append(eq)
    df["equity"] = np.round(eqs, 6)
    be, we = s.idxmax(), s.idxmin()
    summary = {
        "scenario": label, "n": int(s.size),
        "cumulative_return_pct": round((eq-1)*100, 4),
        "max_drawdown_pct": round(dd*100, 4),
        "mean_pct": round(s.mean(), 4), "median_pct": round(s.median(), 4),
        "win_rate": round((s > 0).mean(), 4),
        "best_event": df.loc[be, "event_name"], "best_value": round(s.max(), 4),
        "worst_event": df.loc[we, "event_name"], "worst_value": round(s.min(), 4),
        "cum_excl_largest_winner_pct": None, "mean_excl_largest_winner_pct": round(s.drop(be).mean(), 4),
    }
    # cumulative excluding largest winner (re-compound without it)
    s2 = s.drop(be); eq2 = 1.0
    for r in s2:
        eq2 *= (1 + r/100.0)
    summary["cum_excl_largest_winner_pct"] = round((eq2-1)*100, 4)
    return df, summary


def main():
    out = ROOT / "reports" / "ladder_straddle_postmay_v0_5"
    out.mkdir(parents=True, exist_ok=True)
    df = load_all()

    base = [(t, n, "CPI") for t, n in CPI] + [(t, n, "JACKSON_HOLE") for t, n in JH]
    press = base + [(t, n, "FOMC_PRESS_CONFERENCE") for t, n in FOMC_PRESS]
    stmt = base + [(str(pd.Timestamp(t, tz="UTC") - timedelta(minutes=30))[:16], n, "FOMC_STATEMENT")
                   for t, n in FOMC_PRESS]

    rows_press = [run_event(df, t, n, et) for t, n, et in press]
    rows_stmt = [run_event(df, t, n, et) for t, n, et in stmt]

    dfp, sp = aggregate(rows_press, "A_FOMC_press_conf")
    dfs, ss = aggregate(rows_stmt, "B_FOMC_statement")

    dfp.to_csv(out / "event_results_FOMC_pressconf.csv", index=False)
    dfs.to_csv(out / "event_results_FOMC_statement.csv", index=False)
    comp = pd.DataFrame([sp, ss])
    comp.to_csv(out / "scenario_comparison.csv", index=False)

    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print("=== PER-EVENT portfolio_net_pct (FOMC = press-conf anchor) ===")
    print(dfp[["event_name", "event_type", "long_leg_gross_pct", "long_exit", "short_leg_gross_pct",
               "short_exit", "portfolio_net_pct", "equity"]].to_string(index=False))
    print("\n=== FOMC events only: press-conf vs statement anchor ===")
    fp = dfp[dfp.event_type.str.startswith("FOMC")][["event_name", "portfolio_net_pct"]].rename(
        columns={"portfolio_net_pct": "press_conf_net"})
    fs = dfs[dfs.event_type.str.startswith("FOMC")][["event_name", "portfolio_net_pct"]].rename(
        columns={"portfolio_net_pct": "statement_net"})
    print(fp.merge(fs, on="event_name").to_string(index=False))
    print("\n=== SCENARIO COMPARISON (full 14-event portfolio, net of 0.20%/event) ===")
    print(comp[["scenario", "n", "cumulative_return_pct", "max_drawdown_pct", "win_rate", "mean_pct",
                "best_event", "worst_event", "cum_excl_largest_winner_pct",
                "mean_excl_largest_winner_pct"]].to_string(index=False))

    _summary(out, dfp, dfs, comp)
    print(f"\n[out] {out}")


def _summary(out, dfp, dfs, comp):
    def tbl(df, cols):
        return "\n".join(["| "+" | ".join(cols)+" |", "|"+"|".join(["---"]*len(cols))+"|"] +
                         ["| "+" | ".join(str(r[c]) for c in cols)+" |" for _, r in df.iterrows()])
    L = ["# v0.5 — Ladder-exit 50/50 straddle, post-May 2025 (14 events)\n",
         "Full position, 50% long + 50% short. Entry = anchor − 1 min. Net of costs "
         "(0.10% open + 0.10% close per leg = 0.20% of capital per event; 0.05% fee + 0.05% slippage "
         "each side). FOMC tested under press-conf (14:30 ET) and statement (14:00 ET) anchors.\n",
         "Price treated as continuous: 3% / 5% / 2% / 1% fill at the exact level (detected via 1m "
         "high/low); only 'market' exits use the discrete minute price.\n",
         "## Scenario comparison (14-event portfolio, net)",
         tbl(comp, ["scenario", "n", "cumulative_return_pct", "max_drawdown_pct", "win_rate",
                    "best_event", "worst_event", "cum_excl_largest_winner_pct",
                    "mean_excl_largest_winner_pct"]), "",
         "## FOMC events: press-conf vs statement (per-event net %)",
         tbl(dfp[dfp.event_type.str.startswith("FOMC")][["event_name", "portfolio_net_pct"]]
             .rename(columns={"portfolio_net_pct": "press_conf_net"})
             .merge(dfs[dfs.event_type.str.startswith("FOMC")][["event_name", "portfolio_net_pct"]]
                    .rename(columns={"portfolio_net_pct": "statement_net"}), on="event_name"),
             ["event_name", "press_conf_net", "statement_net"]), "",
         "## Assumptions you may want to correct",
         "- Each leg simulated independently: the leg that breaks out favorably runs the ladder; the "
         "opposite leg takes the −1% stop. Both legs can end up stopped on a whipsaw (−1% each).",
         "- Branch-B 3-minute wait is timed from the EVENT minute; branch-A 3-minute wait from the "
         "half-sale minute. Remaining-half management starts the candle AFTER the half-sale.",
         "- Same-candle conflicts resolved: −1% stop first, then favorable ladder (5 before 3), then "
         "2%/3% retracement gives, then the market deadline.",
         "- 'Buy 1 minute before' uses the open of the (anchor−1m) candle as entry price.",
         "- n=14 (and only 6 differ between the two FOMC anchors). Single 2025 regime, exploratory — "
         "not a statistical edge claim."]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
