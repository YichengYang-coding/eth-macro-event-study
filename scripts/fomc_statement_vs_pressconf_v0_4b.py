"""
scripts/fomc_statement_vs_pressconf_v0_4b.py
============================================

FOMC-only rerun comparing TWO event anchors on the same 8 FOMC days:

  A. statement-time   : event = 14:00 ET (UTC 18:00 EDT / 19:00 EST)
  B. press-conference : event = 14:30 ET (UTC 18:30 EDT / 19:30 EST)

Both use entry = event-10m and exits +15/+30/+60/+120m (momentum: entry+1m,
exits +5/+15/+30/+60m). No CPI, no Jackson Hole, no OI, no fees, no slippage.
Price-only, unlevered. Strategies reused from v0.1.

Cumulative return / max drawdown use a chronological compounded equity curve
(start 1.0). Straddle per-event metric = combined_pnl_pct (sum of the two
full-notional legs), consistent across A and B for the comparison.
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

# press-conference UTC times (from FOMC metadata); statement = press-conf − 30m
PRESSCONF = [
    ("2025-01-29 19:30", "FOMC_Jan"), ("2025-03-19 18:30", "FOMC_Mar"),
    ("2025-05-07 18:30", "FOMC_May"), ("2025-06-18 18:30", "FOMC_Jun"),
    ("2025-07-30 18:30", "FOMC_Jul"), ("2025-09-17 18:30", "FOMC_Sep"),
    ("2025-10-29 18:30", "FOMC_Oct"), ("2025-12-10 19:30", "FOMC_Dec"),
]
ANCHORS = {
    "A_statement_1400ET":   [(pd.Timestamp(t, tz="UTC") - timedelta(minutes=30), n) for t, n in PRESSCONF],
    "B_pressconf_1430ET":   [(pd.Timestamp(t, tz="UTC"), n) for t, n in PRESSCONF],
}


def load_fomc():
    d = pd.read_csv(ROOT / "data" / "fomc_eth_1m" / "ETHUSDT-1m-fomc_2025_with_utc.csv", encoding="utf-8-sig")
    d["dt"] = pd.to_datetime(d["open_time_utc"]).dt.tz_localize("UTC")
    return d[["dt", "open", "high", "low", "close", "volume"]].drop_duplicates("dt").sort_values("dt").set_index("dt")


def p(df, ev, off, field="open"):
    return v01.price_at(df, ev + timedelta(minutes=off), field)


def agg_curve(pnls_chrono):
    """compound equity (start 1.0) -> (cumulative_return%, max_drawdown%)."""
    eq, peak, dd = 1.0, 1.0, 0.0
    for r in pnls_chrono:
        eq *= (1 + r / 100.0); peak = max(peak, eq); dd = min(dd, eq / peak - 1)
    return round((eq - 1) * 100, 4), round(dd * 100, 4)


def agg(pnl_by_event):
    s = pd.Series(pnl_by_event, dtype=float).dropna()
    if s.empty:
        return None
    be, we = s.idxmax(), s.idxmin()
    cum, mdd = agg_curve(list(s.values))   # s preserves insertion (chronological) order
    return {
        "n": int(s.size), "cumulative_return_pct": cum, "max_drawdown_pct": mdd,
        "mean_pct": round(s.mean(), 4), "median_pct": round(s.median(), 4),
        "win_rate": round((s > 0).mean(), 4),
        "best_event": be, "best_value": round(s.max(), 4),
        "worst_event": we, "worst_value": round(s.min(), 4),
        "mean_excl_largest_winner": round(s.drop(be).mean(), 4) if s.size > 1 else np.nan,
    }


def main():
    out = ROOT / "reports" / "fomc_statement_vs_pressconf_v0_4b"
    out.mkdir(parents=True, exist_ok=True)
    df = load_fomc()

    # ---- verification: all 16 anchor timestamps exist ----
    idx = set(df.index)
    vrows, missing = [], []
    for anchor, evs in ANCHORS.items():
        for ev, name in evs:
            ok = ev in idx
            vrows.append({"anchor": anchor, "event_name": name, "event_utc": ev.strftime("%Y-%m-%d %H:%M"), "exists": ok})
            if not ok:
                missing.append((anchor, name, ev))
    vdf = pd.DataFrame(vrows)
    status = "ALL PASS" if not missing else "MISSING"
    (out / "verification_report.md").write_text(
        f"# v0.4b FOMC anchor verification\n\n## RESULT: {status}\n\n"
        f"16 anchor timestamps (8 statement + 8 press-conf) checked against FOMC 1m data.\n\n"
        + vdf.to_markdown(index=False), encoding="utf-8")
    if missing:
        print("MISSING anchors:", missing); return
    print("verification PASS (16/16 anchor timestamps exist)")

    ret_rows, dir_rows, mom_rows, str_rows = [], [], [], []
    per = {}  # anchor -> config -> {event: pnl}
    for anchor, evs in ANCHORS.items():
        per[anchor] = {}
        for ev, name in evs:
            p10, p0 = p(df, ev, -10), p(df, ev, 0)
            def r(a, b): return round((b / a - 1) * 100, 4)
            ret_rows.append({"anchor": anchor, "event_name": name, "event_utc": ev.strftime("%Y-%m-%d %H:%M"),
                             "ret_-10_+15": r(p10, p(df, ev, 15)), "ret_-10_+30": r(p10, p(df, ev, 30)),
                             "ret_-10_+60": r(p10, p(df, ev, 60)), "ret_-10_+120": r(p10, p(df, ev, 120)),
                             "ret_evt_+15": r(p0, p(df, ev, 15)), "ret_evt_+30": r(p0, p(df, ev, 30)),
                             "ret_evt_+60": r(p0, p(df, ev, 60))})
            for rr in v01.directional(df, ev, "long", 0.0):
                dir_rows.append({"anchor": anchor, "event_name": name, "side": "long", **rr})
                per[anchor].setdefault(f"pre_long_{rr['exit_offset_min']}", {})[name] = rr["pnl_pct"]
            for rr in v01.directional(df, ev, "short", 0.0):
                dir_rows.append({"anchor": anchor, "event_name": name, "side": "short", **rr})
                per[anchor].setdefault(f"pre_short_{rr['exit_offset_min']}", {})[name] = rr["pnl_pct"]
            mm = v01.momentum(df, ev, 0.0)
            for rr in mm["results"]:
                mom_rows.append({"anchor": anchor, "event_name": name, "direction": mm["direction"], **rr})
                per[anchor].setdefault(f"momentum_{rr['exit_after_entry_min']}", {})[name] = rr["pnl_pct"]
            for rr in v01.straddle(df, ev, 0.0):
                rr2 = dict(rr); rr2["anchor"] = anchor; rr2["event_name"] = name
                str_rows.append(rr2)
                per[anchor].setdefault(f"straddle_TP{rr['tp_pct']}_SL{rr['sl_pct']}", {})[name] = rr["combined_pnl_pct"]

    pd.DataFrame(ret_rows).to_csv(out / "event_returns_by_anchor.csv", index=False)
    pd.DataFrame(dir_rows).to_csv(out / "directional_results_by_anchor.csv", index=False)
    pd.DataFrame(mom_rows).to_csv(out / "momentum_results_by_anchor.csv", index=False)
    str_df = pd.DataFrame(str_rows)
    str_df.to_csv(out / "straddle_grid_by_anchor.csv", index=False)

    # ---- aggregate comparison (all configs) ----
    comp = []
    for anchor in ANCHORS:
        for cfg, pe in per[anchor].items():
            a = agg(pe)
            if a:
                strat = ("pre_long" if cfg.startswith("pre_long") else "pre_short" if cfg.startswith("pre_short")
                         else "momentum" if cfg.startswith("momentum") else "straddle")
                comp.append({"anchor": anchor, "strategy": strat, "config": cfg, **a})
    comp_df = pd.DataFrame(comp)
    comp_df.to_csv(out / "aggregate_by_anchor_all_configs.csv", index=False)

    # straddle grid A-vs-B side by side
    sg = comp_df[comp_df.strategy == "straddle"].pivot_table(
        index="config", columns="anchor",
        values=["cumulative_return_pct", "win_rate", "max_drawdown_pct", "mean_excl_largest_winner"])
    sg.to_csv(out / "straddle_grid_comparison.csv")

    # best straddle per anchor by cumulative
    best = (comp_df[comp_df.strategy == "straddle"]
            .sort_values(["anchor", "cumulative_return_pct"], ascending=[True, False])
            .groupby("anchor").head(1))

    _summary(out, comp_df, best)

    pd.set_option("display.width", 260); pd.set_option("display.max_columns", None)
    keycfgs = ["pre_long_60", "pre_long_120", "pre_short_60", "momentum_60", "straddle_TP1.5_SL1.0"]
    print("\n=== A (statement 14:00) vs B (press-conf 14:30) — key configs ===")
    show = comp_df[comp_df.config.isin(keycfgs)].sort_values(["config", "anchor"])
    print(show[["config", "anchor", "n", "cumulative_return_pct", "max_drawdown_pct", "win_rate",
                "mean_pct", "best_event", "worst_event", "mean_excl_largest_winner"]].to_string(index=False))
    print("\n=== best straddle combo per anchor (by cumulative) ===")
    print(best[["anchor", "config", "cumulative_return_pct", "win_rate", "max_drawdown_pct",
                "mean_excl_largest_winner"]].to_string(index=False))
    print(f"\n[out] {out}")


def _summary(out, comp_df, best):
    def row(anchor, cfg, col):
        r = comp_df[(comp_df.anchor == anchor) & (comp_df.config == cfg)]
        return r[col].iloc[0] if len(r) else float("nan")
    A, B = "A_statement_1400ET", "B_pressconf_1430ET"
    def line(label, cfg):
        return (f"| {label} | {row(A,cfg,'cumulative_return_pct')} | {row(A,cfg,'max_drawdown_pct')} | "
                f"{row(A,cfg,'win_rate')} | {row(A,cfg,'mean_excl_largest_winner')} | "
                f"{row(B,cfg,'cumulative_return_pct')} | {row(B,cfg,'max_drawdown_pct')} | "
                f"{row(B,cfg,'win_rate')} | {row(B,cfg,'mean_excl_largest_winner')} |")
    L = ["# v0.4b — FOMC: Statement (14:00 ET) vs Press-Conference (14:30 ET)\n",
         "FOMC-only (8 events). No CPI, no Jackson Hole, no OI, no fees, no slippage. Price-only, "
         "unlevered. Entry −10m; exits +15/+30/+60/+120m (momentum entry+1m, exits +5/+15/+30/+60m). "
         "Cumulative = compounded chronological equity (start 1.0). Straddle metric = combined_pnl_pct.\n",
         "## Key configs — A (statement) vs B (press-conf)",
         "| config | A cum% | A maxDD% | A win | A exclWin | B cum% | B maxDD% | B win | B exclWin |",
         "|---|---|---|---|---|---|---|---|---|",
         line("pre_long +60m", "pre_long_60"),
         line("pre_long +120m", "pre_long_120"),
         line("pre_short +60m", "pre_short_60"),
         line("momentum +60m", "momentum_60"),
         line("straddle TP1.5/SL1.0", "straddle_TP1.5_SL1.0"),
         "",
         f"## Best straddle combo (by cumulative) — A: **{best[best.anchor==A]['config'].iloc[0]}** "
         f"({best[best.anchor==A]['cumulative_return_pct'].iloc[0]}%), "
         f"B: **{best[best.anchor==B]['config'].iloc[0]}** "
         f"({best[best.anchor==B]['cumulative_return_pct'].iloc[0]}%) — exploratory (in-sample), not alpha.\n",
         "## Notes",
         "- n=8 per anchor — tiny sample, 2025 only; structure/plumbing, not an edge claim.",
         "- Statement (14:00) and press-conf (14:30) windows overlap heavily; the 30-min shift mainly "
         "changes which minute is the 'ignition' candle and whether the entry sits before the statement "
         "or between statement and presser.",
         "- `mean_excl_largest_winner` isolates single-event dominance. After-fee not shown (cost-free run).",
         "- Full detail: `aggregate_by_anchor_all_configs.csv`, `straddle_grid_comparison.csv`, "
         "`directional/momentum/straddle_*_by_anchor.csv`, `event_returns_by_anchor.csv`."]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
