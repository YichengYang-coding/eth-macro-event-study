"""
scripts/powell_eth_event_analysis_v0_2.py
=========================================

v0.2 analysis built on top of the v0.1 Powell backtest (same data, same guards:
no NFP, no CPI/PPI/FOMC, no OI, no slippage). Reuses the validated v0.1 helpers.

Adds:
  1. Phase decomposition (pre-drift / immediate / continuation / full move).
  2. Excluding-Jackson-Hole averages (is the edge just one event?).
  3. Per-event excursions over [-180m,+360m]: MFE, MAE, max 1m range, and which
     time segment held the biggest move.
  4. Straddle robustness: per-event PnL for every TP/SL combo, an
     "only_profitable_on_jackson_hole" flag, and the MOST ROBUST combo
     (not the highest-return one). Straddle fees charged on FOUR legs.
  5. Post-event momentum entry-timing sweep: entry = +1m / +3m / +5m,
     exit = entry +15m / +30m / +60m.
  6. final_summary.csv with the requested fields.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# import the validated v0.1 module
_spec = importlib.util.spec_from_file_location(
    "powell_v01", ROOT / "scripts" / "powell_eth_event_backtest_v0_1.py")
v01 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v01)

EVENTS = v01.EVENTS
FEE = v01.BINANCE_TAKER_FEE
JH = "Jackson_Hole"

MOM_ENTRIES = [1, 3, 5]      # minutes after event
MOM_EXITS = [15, 30, 60]     # minutes after entry
SEGMENTS = [("-180..-60", -180, -60), ("-60..0", -60, 0), ("0..+15", 0, 15),
            ("+15..+60", 15, 60), ("+60..+180", 60, 180), ("+180..+360", 180, 360)]


def p(df, event, off, field="open"):
    return v01.price_at(df, event + timedelta(minutes=off), field)


# --- 1. phase decomposition -------------------------------------------------
def phase_decomp(df, event):
    p_60, p_10, p0 = p(df, event, -60), p(df, event, -10), p(df, event, 0)
    p15, p60 = p(df, event, 15), p(df, event, 60)
    def r(a, b): return (b / a - 1) * 100
    return {
        "pre_event_drift_-60_to_event": round(r(p_60, p0), 4),
        "immediate_reaction_event_to_+15": round(r(p0, p15), 4),
        "post_event_continuation_+15_to_+60": round(r(p15, p60), 4),
        "full_event_move_-10_to_+60": round(r(p_10, p60), 4),
    }


# --- 3. excursions over [-180,+360] ----------------------------------------
def excursions(df, event):
    span = v01.window_slice(df, event, 180, 360)
    base = p(df, event, 0)  # anchor = event-time open
    mfe = (span["high"].max() / base - 1) * 100
    mae = (span["low"].min() / base - 1) * 100
    rng = (span["high"] - span["low"])
    max_1m = rng.max()
    max_1m_ts = span.index[rng.values.argmax()]
    # which segment held the biggest high-low span
    seg_ranges = {}
    for label, a, b in SEGMENTS:
        s = span.loc[(span.index >= event + timedelta(minutes=a)) &
                     (span.index <= event + timedelta(minutes=b))]
        seg_ranges[label] = (s["high"].max() - s["low"].min()) if len(s) else np.nan
    biggest_seg = max(seg_ranges, key=lambda k: (seg_ranges[k] if not np.isnan(seg_ranges[k]) else -1))
    return {
        "event_anchor_price": round(base, 2),
        "max_up_180_360_pct": round(mfe, 4),
        "max_down_180_360_pct": round(mae, 4),
        "max_1m_high_low_range": round(max_1m, 2),
        "max_1m_range_time_utc": max_1m_ts.strftime("%Y-%m-%d %H:%M"),
        "biggest_move_segment": biggest_seg,
        "biggest_move_segment_range": round(seg_ranges[biggest_seg], 2),
    }


# --- 5. momentum entry-timing sweep ----------------------------------------
def momentum_timing(df, event):
    first = df.loc[event] if event in df.index else None
    direction = "long" if (first is not None and first["close"] >= first["open"]) else "short"
    rows = []
    for de in MOM_ENTRIES:
        entry = p(df, event, de)
        for ex in MOM_EXITS:
            px = p(df, event, de + ex)
            raw = ((px / entry - 1) if direction == "long" else (1 - px / entry)) * 100
            rows.append({
                "direction": direction, "entry_offset_min": de, "exit_after_entry_min": ex,
                "entry_price": round(entry, 2), "exit_price": round(px, 2),
                "pnl_pct": round(raw, 6),
                "pnl_pct_after_fees": round(raw - FEE * 2 * 100, 6),
            })
    return direction, rows


# ===========================================================================
def main():
    out = ROOT / "reports" / "powell_v0_2"
    out.mkdir(parents=True, exist_ok=True)
    df = v01.load_canonical(ROOT / "data" / "powell_eth_1m")

    phase_rows, exc_rows, mom_rows = [], [], []
    straddle_all = []   # per event full grid
    dir_best = {}       # event -> best directional label/value

    # directional (pre long/short) raw at +60m, momentum best, for "best_directional_strategy"
    for date, name, ev_str in EVENTS:
        event = pd.Timestamp(ev_str, tz="UTC")

        ph = phase_decomp(df, event)
        phase_rows.append({"event_name": name, "event_utc": ev_str, **ph})

        ex = excursions(df, event)
        exc_rows.append({"event_name": name, "event_utc": ev_str, **ex})

        direction, mrows = momentum_timing(df, event)
        for r in mrows:
            mom_rows.append({"event_name": name, **r})

        for r in v01.straddle(df, event, FEE):
            r["event_name"] = name
            straddle_all.append(r)

        # best directional among pre_long@60, pre_short@60, momentum(+1m,+60)
        pl = ((p(df, event, 60) / p(df, event, -10) - 1) * 100)
        ps = -pl
        mm = next(x["pnl_pct"] for x in mrows if x["entry_offset_min"] == 1 and x["exit_after_entry_min"] == 60)
        cand = {"pre_long@+60m": pl, "pre_short@+60m": ps,
                f"momentum_{direction}(+1m,+60m)": mm}
        blabel = max(cand, key=cand.get)
        dir_best[name] = (blabel, round(cand[blabel], 4))

    phase_df = pd.DataFrame(phase_rows)
    exc_df = pd.DataFrame(exc_rows)
    mom_df = pd.DataFrame(mom_rows)
    str_df = pd.DataFrame(straddle_all)

    phase_df.to_csv(out / "phase_decomposition.csv", index=False)
    exc_df.to_csv(out / "event_excursions_180_360.csv", index=False)
    mom_df.to_csv(out / "momentum_entry_timing.csv", index=False)

    # ---- 2. excluding Jackson Hole ----
    def avg_block(df_in, val, label):
        allm = df_in[val].mean()
        exjh = df_in[df_in["event_name"] != JH][val].mean()
        return {"metric": label, "avg_all_4": round(allm, 4),
                "avg_excl_JH": round(exjh, 4),
                "JH_only": round(df_in[df_in["event_name"] == JH][val].mean(), 4)}

    # pre-event long return per exit (use directional from v0.1 recompute here)
    pre_long = []
    for date, name, ev_str in EVENTS:
        event = pd.Timestamp(ev_str, tz="UTC")
        for ex in v01.DIRECTIONAL_EXITS:
            pl = (p(df, event, ex) / p(df, event, -10) - 1) * 100
            pre_long.append({"event_name": name, "exit": ex, "pnl_pct": pl})
    pre_long_df = pd.DataFrame(pre_long)

    excl_rows = []
    for ex in v01.DIRECTIONAL_EXITS:
        sub = pre_long_df[pre_long_df["exit"] == ex]
        excl_rows.append(avg_block(sub, "pnl_pct", f"pre_event_long_exit+{ex}m"))
    # momentum entry+1m per exit
    for ex in MOM_EXITS:
        sub = mom_df[(mom_df["entry_offset_min"] == 1) & (mom_df["exit_after_entry_min"] == ex)]
        excl_rows.append(avg_block(sub, "pnl_pct", f"momentum_entry+1m_exit+{ex}m"))
    # straddle: average combined_pnl_after_fees across the robust-ish mid combo (1.0/1.0)
    for (tp, sl) in [(1.0, 1.0), (1.5, 1.0), (2.0, 1.0)]:
        sub = str_df[(str_df["tp_pct"] == tp) & (str_df["sl_pct"] == sl)]
        excl_rows.append(avg_block(sub, "combined_pnl_pct_after_fees",
                                   f"straddle_TP{tp}_SL{sl}_afterfees"))
    excl_df = pd.DataFrame(excl_rows)
    excl_df.to_csv(out / "excluding_jackson_hole.csv", index=False)

    # ---- 4. straddle robustness across events ----
    rob = []
    n_events = str_df["event_name"].nunique()
    for (tp, sl), g in str_df.groupby(["tp_pct", "sl_pct"]):
        pnl = g["combined_pnl_pct_after_fees"]
        jh_pnl = g.loc[g["event_name"] == JH, "combined_pnl_pct_after_fees"].iloc[0]
        non_jh = g.loc[g["event_name"] != JH, "combined_pnl_pct_after_fees"]
        rob.append({
            "tp_pct": tp, "sl_pct": sl,
            "n_events_profitable_afterfees": int((pnl > 0).sum()),
            "min_pnl_afterfees": round(pnl.min(), 4),     # worst event
            "mean_pnl_afterfees": round(pnl.mean(), 4),
            "median_pnl_afterfees": round(pnl.median(), 4),
            "std_pnl": round(pnl.std(ddof=0), 4),
            "mean_excl_JH": round(non_jh.mean(), 4),
            "only_profitable_on_jackson_hole": bool(jh_pnl > 0 and (non_jh <= 0).all()),
        })
    rob_df = pd.DataFrame(rob)
    # MOST ROBUST = most events profitable, then best worst-case, then highest mean
    rob_df = rob_df.sort_values(
        ["n_events_profitable_afterfees", "min_pnl_afterfees", "mean_pnl_afterfees"],
        ascending=[False, False, False]).reset_index(drop=True)
    rob_df.to_csv(out / "straddle_robustness.csv", index=False)
    robust_pick = rob_df.iloc[0]
    # per-event best straddle (highest after-fee PnL on that event)
    best_straddle_per_event = {}
    for name, g in str_df.groupby("event_name"):
        b = g.loc[g["combined_pnl_pct_after_fees"].idxmax()]
        best_straddle_per_event[name] = f"TP{b['tp_pct']}/SL{b['sl_pct']}"

    # ---- 6. final_summary.csv ----
    fin = []
    for date, name, ev_str in EVENTS:
        event = pd.Timestamp(ev_str, tz="UTC")
        ph = phase_decomp(df, event); ex = excursions(df, event)
        fin.append({
            "event_name": name,
            "event_time_utc": ev_str,
            "pre_60_to_event_return": ph["pre_event_drift_-60_to_event"],
            "event_to_15_return": ph["immediate_reaction_event_to_+15"],
            "event_to_60_return": round((p(df, event, 60) / p(df, event, 0) - 1) * 100, 4),
            "minus10_to_60_return": ph["full_event_move_-10_to_+60"],
            "max_up_180_360": ex["max_up_180_360_pct"],
            "max_down_180_360": ex["max_down_180_360_pct"],
            "best_directional_strategy": f"{dir_best[name][0]} ({dir_best[name][1]:+}%)",
            "best_straddle_setting": best_straddle_per_event[name],
        })
    fin_df = pd.DataFrame(fin)
    fin_df.to_csv(out / "final_summary.csv", index=False)

    # ---- console + summary.md ----
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print("=" * 100); print("PHASE DECOMPOSITION (%)"); print("=" * 100)
    print(phase_df.to_string(index=False))
    print("\n" + "=" * 100); print("EXCURSIONS over [-180m,+360m]"); print("=" * 100)
    print(exc_df.to_string(index=False))
    print("\n" + "=" * 100); print("EXCLUDING JACKSON HOLE (avg_all_4 vs avg_excl_JH)"); print("=" * 100)
    print(excl_df.to_string(index=False))
    print("\n" + "=" * 100); print("STRADDLE ROBUSTNESS (top 6 by robustness)"); print("=" * 100)
    print(rob_df.head(6).to_string(index=False))
    print(f"\nMOST ROBUST straddle: TP{robust_pick['tp_pct']}/SL{robust_pick['sl_pct']} "
          f"(profitable on {robust_pick['n_events_profitable_afterfees']}/{n_events} events, "
          f"worst={robust_pick['min_pnl_afterfees']}, mean={robust_pick['mean_pnl_afterfees']}, "
          f"mean_excl_JH={robust_pick['mean_excl_JH']})")
    print("\n" + "=" * 100); print("MOMENTUM ENTRY-TIMING (raw pnl_pct)"); print("=" * 100)
    print(mom_df.pivot_table(index=["event_name", "direction", "entry_offset_min"],
                             columns="exit_after_entry_min", values="pnl_pct").round(4).to_string())
    print("\n" + "=" * 100); print("FINAL SUMMARY"); print("=" * 100)
    print(fin_df.to_string(index=False))

    _write_summary(out / "powell_v0_2_summary.md", phase_df, exc_df, excl_df,
                   rob_df, robust_pick, fin_df, n_events)
    print(f"\n[out] {out} (phase_decomposition, event_excursions_180_360, excluding_jackson_hole,")
    print( "       straddle_robustness, momentum_entry_timing, final_summary, summary.md)")


def _write_summary(path, phase_df, exc_df, excl_df, rob_df, robust, fin_df, n):
    def tbl(df):
        c = list(df.columns)
        return "\n".join(["| " + " | ".join(c) + " |", "|" + "|".join(["---"] * len(c)) + "|"] +
                         ["| " + " | ".join(str(r[x]) for x in c) + " |" for _, r in df.iterrows()])
    L = ["# Powell ETH 1m — v0.2 Analysis Summary\n",
         "Built on v0.1 (same data/guards: no NFP, no CPI/PPI/FOMC, no OI, no slippage). "
         "Raw PnL uses fee=0; `*_after_fees` apply Binance taker 0.05%/side; straddle fees are "
         "charged on **four legs** (2 entries + 2 exits = 0.20%).\n",
         "## 1. Phase decomposition (%)", tbl(phase_df), "",
         "## 3. Excursions over [-180m,+360m] (anchored at event-time price)", tbl(exc_df), "",
         "## 2. Excluding Jackson Hole — is the edge one event?",
         tbl(excl_df),
         "\n> If `avg_excl_JH` collapses toward ~0 or negative while `avg_all_4` is positive, the "
         "result is carried by Jackson Hole alone.\n",
         "## 4. Straddle robustness (most robust, not highest return)",
         f"- **Most robust combo: TP{robust['tp_pct']}/SL{robust['sl_pct']}** — profitable on "
         f"{robust['n_events_profitable_afterfees']}/{n} events, worst-event "
         f"{robust['min_pnl_afterfees']}%, mean {robust['mean_pnl_afterfees']}%, "
         f"mean excl-JH {robust['mean_excl_JH']}%.",
         "- Robustness ranking = (#events profitable after fees) → (best worst-case) → (highest mean). "
         "Per-combo per-event PnL and an `only_profitable_on_jackson_hole` flag are in "
         "`straddle_robustness.csv` / `strategy_straddle_grid` (v0.1).\n",
         "## 5. Momentum entry-timing", "Entry +1m/+3m/+5m × exit +15/+30/+60m in "
         "`momentum_entry_timing.csv` (direction from the first 1m candle).\n",
         "## 6. final_summary.csv", tbl(fin_df), "",
         "## Caveat", "n=4 with one outlier (Jackson Hole). The excluding-JH block is the key "
         "robustness lens; everything else is structure, not an edge estimate."]
    path.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
