"""
scripts/eth_event_backtest_v0_2_powell_nfp.py
=============================================

v0.2 = v0.1 strategies extended to add the 11 calendar-2025 NFP / Employment
Situation events alongside the 4 Powell events.

Regime scope (intentional): 2025 ONLY. This is a phase-specific exploratory
test, NOT a permanent cross-cycle strategy. No 2021-2024.

Guards: NO CPI/PPI/FOMC, NO OI, NO slippage. Raw pnl uses fee=0; *_after_fees
apply Binance taker 0.05%/side (straddle = 4 legs). Strategies are identical to
v0.1 (reused from that module). Checkpoints were verified to match raw 1m 100%.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "powell_v01", ROOT / "scripts" / "powell_eth_event_backtest_v0_1.py")
v01 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v01)

FEE = v01.BINANCE_TAKER_FEE

# --- combined event universe (4 Powell + 11 NFP), 2025 only -----------------
POWELL = [
    ("2025-06-24", "Powell_Testimony_House", "2025-06-24 14:00", "Powell"),
    ("2025-08-22", "Jackson_Hole",           "2025-08-22 14:00", "Powell"),
    ("2025-09-23", "Economic_Outlook",       "2025-09-23 16:35", "Powell"),
    ("2025-10-14", "NABE",                   "2025-10-14 16:20", "Powell"),
]
NFP = [
    ("2025-01-10", "NFP_Dec2024",          "2025-01-10 13:30", "NFP"),
    ("2025-02-07", "NFP_Jan2025",          "2025-02-07 13:30", "NFP"),
    ("2025-03-07", "NFP_Feb2025",          "2025-03-07 13:30", "NFP"),
    ("2025-04-04", "NFP_Mar2025",          "2025-04-04 12:30", "NFP"),
    ("2025-05-02", "NFP_Apr2025",          "2025-05-02 12:30", "NFP"),
    ("2025-06-06", "NFP_May2025",          "2025-06-06 12:30", "NFP"),
    ("2025-07-03", "NFP_Jun2025",          "2025-07-03 12:30", "NFP"),
    ("2025-08-01", "NFP_Jul2025",          "2025-08-01 12:30", "NFP"),
    ("2025-09-05", "NFP_Aug2025",          "2025-09-05 12:30", "NFP"),
    ("2025-11-20", "NFP_Sep2025_Delayed",  "2025-11-20 13:30", "NFP"),
    ("2025-12-16", "NFP_Nov2025_Delayed",  "2025-12-16 13:30", "NFP"),
]
EVENTS = POWELL + NFP


# ---------------------------------------------------------------------------
def load_combined_canonical() -> pd.DataFrame:
    # Powell file: open_time_utc "%Y/%m/%d %H:%M"
    pw = pd.read_csv(ROOT / "data" / "powell_eth_1m" / "ETHUSDT-1m-4days_with_utc.csv",
                     encoding="utf-8-sig")
    pw["dt"] = pd.to_datetime(pw["open_time_utc"], format="%Y/%m/%d %H:%M").dt.tz_localize("UTC")
    # NFP file: ISO open_time_utc
    nf = pd.read_csv(ROOT / "data" / "nfp_eth_1m" / "ETHUSDT-1m-nfp2025_with_utc.csv",
                     encoding="utf-8-sig")
    nf["dt"] = pd.to_datetime(nf["open_time_utc"]).dt.tz_localize("UTC")
    keep = ["dt", "open", "high", "low", "close", "volume", "num_trades"]
    df = pd.concat([pw[keep], nf[keep]], ignore_index=True)
    df = df.drop_duplicates("dt").sort_values("dt").reset_index(drop=True)
    return df.set_index("dt")


def p(df, event, off, field="open"):
    return v01.price_at(df, event + timedelta(minutes=off), field)


# --- per-event returns + new range/vol metrics ------------------------------
def event_metrics(df, event):
    p10, p0 = p(df, event, -10), p(df, event, 0)
    p15, p30, p60 = p(df, event, 15), p(df, event, 30), p(df, event, 60)
    def r(a, b): return np.nan if (np.isnan(a) or np.isnan(b)) else (b / a - 1) * 100

    sp_e60 = v01.window_slice(df, event, 0, 60)            # [event, +60]
    sp_6060 = v01.window_slice(df, event, 60, 60)          # [-60, +60]
    hl_e60 = sp_e60["high"].max() - sp_e60["low"].min()
    hl_6060 = sp_6060["high"].max() - sp_6060["low"].min()
    # realized vol over [-60,+60] from 1m close-to-close log returns
    rets = np.log(sp_6060["close"] / sp_6060["close"].shift(1)).dropna()
    rv = float(np.sqrt((rets ** 2).sum()) * 100)

    return {
        "ret_-10m_to_+15m": round(r(p10, p15), 4),
        "ret_-10m_to_+30m": round(r(p10, p30), 4),
        "ret_-10m_to_+60m": round(r(p10, p60), 4),
        "ret_event_to_+15m": round(r(p0, p15), 4),
        "ret_event_to_+30m": round(r(p0, p30), 4),
        "ret_event_to_+60m": round(r(p0, p60), 4),
        "hl_range_event_to_+60m": round(hl_e60, 2),
        "hl_range_event_to_+60m_pct": round(hl_e60 / p0 * 100, 4),
        "hl_range_-60m_to_+60m": round(hl_6060, 2),
        "hl_range_-60m_to_+60m_pct": round(hl_6060 / p0 * 100, 4),
        "realized_vol_-60_+60_pct": round(rv, 4),
    }


# --- aggregation with exclude-winner / exclude-loser ------------------------
def aggregate(values: dict) -> dict:
    s = pd.Series(values, dtype=float).dropna()
    if s.empty:
        return {k: np.nan for k in (
            "n", "mean", "median", "win_rate", "best_event", "best_value",
            "worst_event", "worst_value", "mean_excl_largest_winner",
            "mean_excl_largest_loser")}
    be, we = s.idxmax(), s.idxmin()
    return {
        "n": int(s.size), "mean": round(s.mean(), 4), "median": round(s.median(), 4),
        "win_rate": round((s > 0).mean(), 4),
        "best_event": be, "best_value": round(s.max(), 4),
        "worst_event": we, "worst_value": round(s.min(), 4),
        "mean_excl_largest_winner": round(s.drop(be).mean(), 4) if s.size > 1 else np.nan,
        "mean_excl_largest_loser": round(s.drop(we).mean(), 4) if s.size > 1 else np.nan,
    }


# ===========================================================================
def main():
    out = ROOT / "reports" / "powell_nfp_v0_2"
    (out / "windows").mkdir(parents=True, exist_ok=True)
    (out / "charts").mkdir(parents=True, exist_ok=True)
    df = load_combined_canonical()

    meta_rows, cp_rows, ret_rows = [], [], []
    dir_rows, mom_rows, str_rows = [], [], []

    for date, name, ev_str, group in EVENTS:
        event = pd.Timestamp(ev_str, tz="UTC")
        meta_rows.append({"event_date": date, "event_name": name, "event_type": group,
                          "event_time_utc": ev_str})

        # 3 windows
        for wname, (pre, post) in v01.WINDOWS.items():
            w = v01.window_slice(df, event, pre, post).reset_index()
            w.rename(columns={"dt": "datetime_utc"}, inplace=True)
            w["datetime_utc"] = w["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
            w.to_csv(out / "windows" / f"{date}_{name}_{wname}.csv", index=False)

        # checkpoints
        cp = {off: p(df, event, off) for off in v01.CHECKPOINT_OFFSETS}
        cp_rows.append({"event_date": date, "event_name": name, "group": group, "event_utc": ev_str,
                        **{f"p_{k:+d}m": (None if np.isnan(v) else round(v, 2)) for k, v in cp.items()}})

        # returns + extra metrics
        em = event_metrics(df, event)
        ret_rows.append({"event_name": name, "group": group, "event_utc": ev_str, **em})

        # strategies (reused from v0.1)
        for side, key in (("long", "strat1_pre_long"), ("short", "strat2_pre_short")):
            for rrow in v01.directional(df, event, side, FEE):
                dir_rows.append({"event_name": name, "group": group, "strategy": key,
                                 "side": side, **rrow})
        m = v01.momentum(df, event, FEE)
        for rrow in m["results"]:
            mom_rows.append({"event_name": name, "group": group, "strategy": "strat4_momentum",
                             "direction": m["direction"], **rrow})
        for rrow in v01.straddle(df, event, FEE):
            rrow["event_name"] = name; rrow["group"] = group
            str_rows.append(rrow)

        # chart
        v01.make_chart(df, event, name, out / "charts" / f"{date}_{name}.png")

    meta_df = pd.DataFrame(meta_rows)
    cp_df = pd.DataFrame(cp_rows)
    ret_df = pd.DataFrame(ret_rows)
    dir_df = pd.DataFrame(dir_rows)
    mom_df = pd.DataFrame(mom_rows)
    str_df = pd.DataFrame(str_rows)

    meta_df.to_csv(out / "event_metadata_v0_2.csv", index=False)
    cp_df.to_csv(out / "checkpoint_prices.csv", index=False)
    ret_df.to_csv(out / "event_returns.csv", index=False)
    dir_df.to_csv(out / "strategy_directional.csv", index=False)
    mom_df.to_csv(out / "strategy_momentum.csv", index=False)
    str_df.to_csv(out / "strategy_straddle_grid.csv", index=False)

    # ---- grouped aggregates (a Powell / b NFP / c combined) ----
    def grp_events(g):
        return None if g == "ALL" else g

    agg_dir, agg_mom, agg_str = [], [], []
    for g in ("Powell", "NFP", "ALL"):
        sub_dir = dir_df if g == "ALL" else dir_df[dir_df["group"] == g]
        for side in ("long", "short"):
            for ex in v01.DIRECTIONAL_EXITS:
                rows = sub_dir[(sub_dir["side"] == side) & (sub_dir["exit_offset_min"] == ex)]
                raw = dict(zip(rows["event_name"], rows["pnl_pct"]))
                fee = dict(zip(rows["event_name"], rows["pnl_pct_after_fees"]))
                a = aggregate(raw)
                agg_dir.append({"group": g, "strategy": f"pre_{side}", "exit_offset_min": ex,
                                **a, "mean_afterfees": round(pd.Series(fee).mean(), 4),
                                "win_rate_afterfees": round((pd.Series(fee) > 0).mean(), 4)})
        sub_mom = mom_df if g == "ALL" else mom_df[mom_df["group"] == g]
        for ex in v01.MOMENTUM_EXITS:
            rows = sub_mom[sub_mom["exit_after_entry_min"] == ex]
            raw = dict(zip(rows["event_name"], rows["pnl_pct"]))
            fee = dict(zip(rows["event_name"], rows["pnl_pct_after_fees"]))
            a = aggregate(raw)
            agg_mom.append({"group": g, "strategy": "momentum_entry+1m", "exit_after_entry_min": ex,
                            **a, "mean_afterfees": round(pd.Series(fee).mean(), 4),
                            "win_rate_afterfees": round((pd.Series(fee) > 0).mean(), 4)})
        sub_str = str_df if g == "ALL" else str_df[str_df["group"] == g]
        for (tp, sl), gg in sub_str.groupby(["tp_pct", "sl_pct"]):
            raw = dict(zip(gg["event_name"], gg["combined_pnl_pct"]))
            fee = dict(zip(gg["event_name"], gg["combined_pnl_pct_after_fees"]))
            a = aggregate(fee)  # straddle aggregated on AFTER-FEES (4 legs)
            agg_str.append({"group": g, "tp_pct": tp, "sl_pct": sl, **a,
                            "mean_raw": round(pd.Series(raw).mean(), 4)})

    agg_dir_df = pd.DataFrame(agg_dir)
    agg_mom_df = pd.DataFrame(agg_mom)
    agg_str_df = pd.DataFrame(agg_str)
    agg_dir_df.to_csv(out / "aggregate_directional.csv", index=False)
    agg_mom_df.to_csv(out / "aggregate_momentum.csv", index=False)
    agg_str_df.to_csv(out / "aggregate_straddle.csv", index=False)

    # most robust straddle per group (after fees): #profitable -> worst-case -> mean
    robust = (agg_str_df.sort_values(["group", "win_rate", "worst_value", "mean"],
                                     ascending=[True, False, False, False])
              .groupby("group").head(1))

    _summary(out, meta_df, ret_df, agg_dir_df, agg_mom_df, agg_str_df, robust)

    # ---- console ----
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", None)
    print("=" * 110); print("EVENT RETURNS + RANGE/VOL (15 events)"); print("=" * 110)
    print(ret_df[["event_name", "group", "ret_-10m_to_+60m", "ret_event_to_+60m",
                  "hl_range_event_to_+60m_pct", "hl_range_-60m_to_+60m_pct",
                  "realized_vol_-60_+60_pct"]].to_string(index=False))
    print("\n" + "=" * 110); print("AGGREGATE — pre_event_long @ +60m (raw)"); print("=" * 110)
    print(agg_dir_df[(agg_dir_df.strategy == "pre_long") & (agg_dir_df.exit_offset_min == 60)]
          [["group", "n", "mean", "median", "win_rate", "best_event", "best_value",
            "worst_event", "worst_value", "mean_excl_largest_winner",
            "mean_excl_largest_loser", "mean_afterfees"]].to_string(index=False))
    print("\n" + "=" * 110); print("AGGREGATE — momentum entry+1m @ +60m (raw)"); print("=" * 110)
    print(agg_mom_df[agg_mom_df.exit_after_entry_min == 60]
          [["group", "n", "mean", "median", "win_rate", "best_event", "worst_event",
            "mean_excl_largest_winner", "mean_excl_largest_loser", "mean_afterfees"]].to_string(index=False))
    print("\n" + "=" * 110); print("MOST ROBUST straddle per group (after 4-leg fees)"); print("=" * 110)
    print(robust[["group", "tp_pct", "sl_pct", "n", "mean", "median", "win_rate",
                  "worst_value", "mean_excl_largest_winner"]].to_string(index=False))
    print(f"\n[out] {out}  (metadata, 45 window CSVs, 15 charts, checkpoints, returns,")
    print( "       3 strategy CSVs, 3 aggregate CSVs, summary.md)")


def _summary(out, meta, ret, ad, am, asr, robust):
    def tbl(df, cols):
        d = df[cols]
        return "\n".join(["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"] +
                         ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in d.iterrows()])
    L = ["# ETH 1m Event Backtest — v0.2 (Powell + 2025 NFP)\n",
         "**2025 exploratory regime test — NOT a statistical edge claim.** Phase-specific to the "
         "2025 crypto regime; not extended to 2021-2024.\n",
         "Guards: no CPI/PPI/FOMC, no OI, no slippage. Raw pnl uses fee=0; `*_after_fees` apply "
         "Binance taker 0.05%/side (straddle on 4 legs). Strategies identical to v0.1. "
         "Checkpoints verified to match raw 1m 100% (121/121 OHLCV).\n",
         "## Event universe (15)",
         "- Powell (4): Testimony 06-24, Jackson Hole 08-22, Economic Outlook 09-23, NABE 10-14.",
         "- NFP (11): the actual 2025 Employment Situation releases; 10-03 and 11-07 excluded "
         "(no report released). Sep & Nov reports were delayed (released 11-20 and 12-16).\n",
         "## pre_event_long @ +60m (raw pnl_pct) — Powell / NFP / combined",
         tbl(ad[(ad.strategy == "pre_long") & (ad.exit_offset_min == 60)],
             ["group", "n", "mean", "median", "win_rate", "best_event", "worst_event",
              "mean_excl_largest_winner", "mean_excl_largest_loser", "mean_afterfees"]), "",
         "## momentum entry+1m @ +60m (raw pnl_pct)",
         tbl(am[am.exit_after_entry_min == 60],
             ["group", "n", "mean", "median", "win_rate", "best_event", "worst_event",
              "mean_excl_largest_winner", "mean_excl_largest_loser", "mean_afterfees"]), "",
         "## Most robust straddle per group (after 4-leg fees; robust = #profitable → worst-case → mean)",
         tbl(robust, ["group", "tp_pct", "sl_pct", "n", "mean", "median", "win_rate",
                      "worst_value", "mean_excl_largest_winner"]), "",
         "## Notes",
         "- `excluding largest winner / loser` columns isolate single-event dominance.",
         "- Full per-event detail: `event_returns.csv` (incl. high-low ranges event→+60m and "
         "−60→+60m, and realized vol −60→+60m from 1m log returns), `strategy_*` CSVs, and the "
         "`aggregate_*` CSVs for every config × group.",
         "- n is small (Powell=4, NFP=11). Treat as structure/plumbing, not edge."]
    (out / "powell_nfp_v0_2_summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
