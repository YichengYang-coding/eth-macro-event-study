"""
scripts/cpi_ppi_event_backtest_v0_3a.py
=======================================

v0.3a — CPI/PPI 2025 event-day price-reaction backtest (ETHUSDT Binance USD-M
perpetual, 1m, historical, UTC). Price-only. Unlevered: pnl_pct is a price-based
notional return.

Guards: no leverage, no OI, no slippage, no CPI/PPI surprise data, no fake OI
momentum. Raw pnl uses fee=0; *_after_fees apply Binance taker 0.05%/side
(straddle on 4 legs). Strategies identical to v0.1 (reused).

2025 exploratory regime test — NOT a statistical edge claim.

Runs Step-1 data verification first and writes verification_report.md; only
proceeds to the backtest if every check passes.
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

DATA = ROOT / "data" / "cpi_ppi_eth_1m"
COMBINED = "ETHUSDT-1m-cpi_ppi_2025_with_utc.csv"
META = "event_metadata_cpi_ppi_2025.csv"
CHECK = "event_checkpoints_cpi_ppi_2025.csv"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_canonical() -> pd.DataFrame:
    raw = pd.read_csv(DATA / COMBINED, encoding="utf-8-sig")
    raw["dt"] = pd.to_datetime(raw["open_time_utc"]).dt.tz_localize("UTC")
    keep = ["dt", "open", "high", "low", "close", "volume", "num_trades"]
    return raw[keep].drop_duplicates("dt").sort_values("dt").reset_index(drop=True).set_index("dt")


def load_events() -> list:
    md = pd.read_csv(DATA / META, encoding="utf-8-sig")
    md["event_time_utc"] = pd.to_datetime(md["event_time_utc"])
    ev = []
    for _, r in md.iterrows():
        ev.append((r["event_date"], r["event_name"], r["event_type"],
                   r["event_time_utc"].strftime("%Y-%m-%d %H:%M")))
    return ev


def p(df, event, off, field="open"):
    return v01.price_at(df, event + timedelta(minutes=off), field)


# ---------------------------------------------------------------------------
# Step 1 verification (re-run, write report)
# ---------------------------------------------------------------------------
def verify(df, out: Path) -> bool:
    raw = df.reset_index()
    per_day = raw.groupby(raw["dt"].dt.date).size()
    chk_1440 = set(per_day.unique()) == {1440}
    chk_nodup = int(raw["dt"].duplicated().sum()) == 0

    ck = pd.read_csv(DATA / CHECK, encoding="utf-8-sig")
    ck["ts"] = pd.to_datetime(ck["timestamp_utc"]).dt.tz_localize("UTC")
    ck["evt"] = pd.to_datetime(ck["event_time_utc"]).dt.tz_localize("UTC")
    chk_off = bool((ck["evt"] + pd.to_timedelta(ck["offset_min"], unit="m") == ck["ts"]).all())
    m = ck.merge(raw[["dt", "open", "high", "low", "close", "volume"]],
                 left_on="ts", right_on="dt", how="left", suffixes=("_ck", ""))
    missing = int(m["dt"].isna().sum())
    exact = {c: int(np.isclose(m[f"{c}_ck"].astype(float), m[c].astype(float),
                               rtol=0, atol=1e-6).sum()) for c in ["open", "high", "low", "close", "volume"]}
    chk_ohlcv = all(v == len(m) for v in exact.values()) and missing == 0
    allpass = chk_1440 and chk_nodup and chk_off and chk_ohlcv

    L = ["# v0.3a — Data Verification Report (CPI/PPI 2025)\n",
         f"Canonical timestamp column: **open_time_utc**. Raw rows: {len(raw)}; "
         f"unique event dates: {per_day.size}; checkpoints: {len(ck)} "
         f"({ck['event_name'].nunique()} events × {len(ck)//ck['event_name'].nunique()} offsets).\n",
         "| check | result |", "|---|---|",
         f"| 1+3. OHLCV exact match vs raw 1m | {'PASS' if chk_ohlcv else 'FAIL'} "
         f"(open {exact['open']}, high {exact['high']}, low {exact['low']}, "
         f"close {exact['close']}, volume {exact['volume']} / {len(m)}) |",
         f"| 2. timestamp == event_time + offset | {'PASS' if chk_off else 'FAIL'} |",
         f"| 4. each event date has 1440 candles | {'PASS' if chk_1440 else 'FAIL'} "
         f"({sorted(set(per_day.unique()))}) |",
         f"| 5. no duplicate timestamps | {'PASS' if chk_nodup else 'FAIL'} |",
         f"| 6. open_time_utc used as canonical | PASS |",
         f"| rows missing a raw match | {missing} |",
         "",
         f"## RESULT: {'ALL PASS — backtest proceeds' if allpass else 'FAILED — backtest halted'}"]
    out.write_text("\n".join(L), encoding="utf-8")
    return allpass


# ---------------------------------------------------------------------------
# Event metrics
# ---------------------------------------------------------------------------
def event_metrics(df, event):
    p10, p0 = p(df, event, -10), p(df, event, 0)
    p15, p30, p60, p120 = p(df, event, 15), p(df, event, 30), p(df, event, 60), p(df, event, 120)
    def r(a, b): return np.nan if (np.isnan(a) or np.isnan(b)) else (b / a - 1) * 100
    sp_e60 = v01.window_slice(df, event, 0, 60)
    sp_6060 = v01.window_slice(df, event, 60, 60)
    hl_e60 = sp_e60["high"].max() - sp_e60["low"].min()
    hl_6060 = sp_6060["high"].max() - sp_6060["low"].min()
    rets = np.log(sp_6060["close"] / sp_6060["close"].shift(1)).dropna()
    rv = float(np.sqrt((rets ** 2).sum()) * 100)
    return {
        "ret_-10m_to_+15m": round(r(p10, p15), 4),
        "ret_-10m_to_+30m": round(r(p10, p30), 4),
        "ret_-10m_to_+60m": round(r(p10, p60), 4),
        "ret_-10m_to_+120m": round(r(p10, p120), 4),
        "ret_event_to_+15m": round(r(p0, p15), 4),
        "ret_event_to_+30m": round(r(p0, p30), 4),
        "ret_event_to_+60m": round(r(p0, p60), 4),
        "hl_range_event_to_+60m": round(hl_e60, 2),
        "hl_range_event_to_+60m_pct": round(hl_e60 / p0 * 100, 4),
        "hl_range_-60m_to_+60m": round(hl_6060, 2),
        "hl_range_-60m_to_+60m_pct": round(hl_6060 / p0 * 100, 4),
        "realized_vol_-60_+60_pct": round(rv, 4),
    }


# ---------------------------------------------------------------------------
# Aggregation (mean/median/win/best/worst/excl-winner/excl-loser/+drawdown)
# ---------------------------------------------------------------------------
def realized_max_dd(values_by_event_time):
    """Additive equity (start 1.0) over events in chronological order -> max DD %."""
    s = [v for _, v in sorted(values_by_event_time) if not np.isnan(v)]
    eq, peak, worst = 1.0, 1.0, 0.0
    for v in s:
        eq += v / 100.0
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1.0)
    return round(worst * 100, 4)


def aggregate(raw_map, fee_map, time_map):
    s = pd.Series(raw_map, dtype=float).dropna()
    f = pd.Series(fee_map, dtype=float).dropna()
    if s.empty:
        return None
    be, we = s.idxmax(), s.idxmin()
    return {
        "n": int(s.size), "mean_raw": round(s.mean(), 4), "median_raw": round(s.median(), 4),
        "win_rate_raw": round((s > 0).mean(), 4),
        "best_event": be, "best_value": round(s.max(), 4),
        "worst_event": we, "worst_value": round(s.min(), 4),
        "mean_excl_largest_winner": round(s.drop(be).mean(), 4) if s.size > 1 else np.nan,
        "mean_excl_largest_loser": round(s.drop(we).mean(), 4) if s.size > 1 else np.nan,
        "mean_afterfees": round(f.mean(), 4),
        "win_rate_afterfees": round((f > 0).mean(), 4),
        "realized_max_dd_raw_pct": realized_max_dd([(time_map[k], raw_map[k]) for k in raw_map]),
    }


# ===========================================================================
def main():
    out = ROOT / "reports" / "cpi_ppi_v0_3a"
    (out / "windows").mkdir(parents=True, exist_ok=True)
    (out / "charts").mkdir(parents=True, exist_ok=True)
    df = load_canonical()

    # ---- Step 1 verification gate ----
    if not verify(df, out / "verification_report.md"):
        print("VERIFICATION FAILED — see verification_report.md; halting.")
        return
    print("Step 1 verification PASS -> running backtest")

    events = load_events()
    cp_rows, ret_rows = [], []
    long_rows, short_rows, mom_rows, str_rows = [], [], [], []

    for date, name, etype, ev_str in events:
        event = pd.Timestamp(ev_str, tz="UTC")
        for wname, (pre, post) in v01.WINDOWS.items():
            w = v01.window_slice(df, event, pre, post).reset_index()
            w.rename(columns={"dt": "datetime_utc"}, inplace=True)
            w["datetime_utc"] = w["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
            w.to_csv(out / "windows" / f"{date}_{name}_{wname}.csv", index=False)

        cp = {off: p(df, event, off) for off in v01.CHECKPOINT_OFFSETS}
        cp_rows.append({"event_date": date, "event_name": name, "event_type": etype, "event_utc": ev_str,
                        **{f"p_{k:+d}m": (None if np.isnan(v) else round(v, 2)) for k, v in cp.items()}})
        ret_rows.append({"event_name": name, "event_type": etype, "event_utc": ev_str,
                         **event_metrics(df, event)})

        for rr in v01.directional(df, event, "long", FEE):
            long_rows.append({"event_name": name, "event_type": etype, **rr})
        for rr in v01.directional(df, event, "short", FEE):
            short_rows.append({"event_name": name, "event_type": etype, **rr})
        mm = v01.momentum(df, event, FEE)
        for rr in mm["results"]:
            mom_rows.append({"event_name": name, "event_type": etype, "direction": mm["direction"], **rr})
        for rr in v01.straddle(df, event, FEE):
            rr["event_name"] = name; rr["event_type"] = etype
            str_rows.append(rr)

        v01.make_chart(df, event, name, out / "charts" / f"{date}_{name}.png")

    cp_df = pd.DataFrame(cp_rows); ret_df = pd.DataFrame(ret_rows)
    long_df = pd.DataFrame(long_rows); short_df = pd.DataFrame(short_rows)
    mom_df = pd.DataFrame(mom_rows); str_df = pd.DataFrame(str_rows)

    cp_df.to_csv(out / "checkpoint_prices.csv", index=False)
    ret_df.to_csv(out / "event_returns.csv", index=False)
    long_df.to_csv(out / "pre_event_long_results.csv", index=False)
    short_df.to_csv(out / "pre_event_short_results.csv", index=False)
    mom_df.to_csv(out / "post_event_momentum_results.csv", index=False)
    str_df.to_csv(out / "straddle_grid_results.csv", index=False)

    # time map for drawdown ordering
    tmap = {name: pd.Timestamp(ev, tz="UTC") for _, name, _, ev in events}

    def add_aggs(rows, df_in, value_col, fee_col, label_fn, by):
        for g in ("CPI", "PPI", "ALL"):
            sub = df_in if g == "ALL" else df_in[df_in["event_type"] == g]
            for key, gg in sub.groupby(by):
                raw_map = dict(zip(gg["event_name"], gg[value_col]))
                fee_map = dict(zip(gg["event_name"], gg[fee_col]))
                a = aggregate(raw_map, fee_map, tmap)
                if a:
                    rows.append({"event_type": g, **label_fn(key), **a})

    agg = []
    add_aggs(agg, long_df, "pnl_pct", "pnl_pct_after_fees",
             lambda k: {"strategy": "pre_long", "config": f"exit+{k}m"}, "exit_offset_min")
    add_aggs(agg, short_df, "pnl_pct", "pnl_pct_after_fees",
             lambda k: {"strategy": "pre_short", "config": f"exit+{k}m"}, "exit_offset_min")
    add_aggs(agg, mom_df, "pnl_pct", "pnl_pct_after_fees",
             lambda k: {"strategy": "momentum_entry+1m", "config": f"exit+{k}m"}, "exit_after_entry_min")
    add_aggs(agg, str_df, "combined_pnl_pct", "combined_pnl_pct_after_fees",
             lambda k: {"strategy": "straddle", "config": f"TP{k[0]}/SL{k[1]}"}, ["tp_pct", "sl_pct"])
    agg_df = pd.DataFrame(agg)
    agg_df.to_csv(out / "aggregate_by_event_type.csv", index=False)

    _summary(out, ret_df, agg_df)

    # console
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", None)
    print("\n=== EVENT RETURNS (-10->+60) + vol, by type ===")
    print(ret_df[["event_name", "event_type", "ret_-10m_to_+60m", "ret_event_to_+60m",
                  "hl_range_-60m_to_+60m_pct", "realized_vol_-60_+60_pct"]].to_string(index=False))
    for strat, cfg in [("pre_long", "exit+60m"), ("pre_short", "exit+60m"),
                       ("momentum_entry+1m", "exit+60m")]:
        print(f"\n=== AGG {strat} {cfg} (raw) ===")
        print(agg_df[(agg_df.strategy == strat) & (agg_df.config == cfg)]
              [["event_type", "n", "mean_raw", "median_raw", "win_rate_raw", "best_event",
                "worst_event", "mean_excl_largest_winner", "mean_excl_largest_loser",
                "mean_afterfees", "realized_max_dd_raw_pct"]].to_string(index=False))
    print("\n=== most robust straddle per type (after-fees: #profitable->worst->mean) ===")
    rob = (agg_df[agg_df.strategy == "straddle"]
           .sort_values(["event_type", "win_rate_afterfees", "worst_value", "mean_afterfees"],
                        ascending=[True, False, False, False]).groupby("event_type").head(1))
    print(rob[["event_type", "config", "n", "mean_afterfees", "win_rate_afterfees",
               "worst_value", "mean_excl_largest_winner"]].to_string(index=False))
    print(f"\n[out] {out} (verification_report, checkpoints, returns, 4 strategy CSVs,")
    print( "       aggregate_by_event_type, summary.md, 21 charts, 63 window CSVs)")


def _summary(out, ret_df, agg_df):
    def tbl(df, cols):
        d = df[cols]
        return "\n".join(["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"] +
                         ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in d.iterrows()])
    nl = ret_df.groupby("event_type").size().to_dict()
    pl = agg_df[(agg_df.strategy == "pre_long") & (agg_df.config == "exit+60m")]
    ps = agg_df[(agg_df.strategy == "pre_short") & (agg_df.config == "exit+60m")]
    mo = agg_df[(agg_df.strategy == "momentum_entry+1m") & (agg_df.config == "exit+60m")]
    cols = ["event_type", "n", "mean_raw", "median_raw", "win_rate_raw", "best_event",
            "worst_event", "mean_excl_largest_winner", "mean_excl_largest_loser",
            "mean_afterfees", "realized_max_dd_raw_pct"]

    # divergence read
    def afterfee(d, et):
        row = d[d.event_type == et]
        return float(row["mean_afterfees"].iloc[0]) if len(row) else float("nan")
    verdicts = []
    for label, d in [("pre_event_long@+60m", pl), ("pre_event_short@+60m", ps),
                     ("post_event_momentum@+60m", mo)]:
        cpi, ppi = afterfee(d, "CPI"), afterfee(d, "PPI")
        verdicts.append(f"- **{label}** after fees: CPI {cpi:+.4f}% vs PPI {ppi:+.4f}% "
                        f"-> {'CPI≥0, PPI<0' if cpi>=0>ppi else 'PPI≥0, CPI<0' if ppi>=0>cpi else 'both≥0' if cpi>=0 and ppi>=0 else 'both<0'}")

    L = ["# v0.3a — CPI/PPI 2025 Event-Reaction Backtest — Summary\n",
         "**2025 exploratory regime test — NOT a statistical edge claim. Price-only.**",
         "ETHUSDT Binance USD-M perpetual, 1m, historical, UTC. Unlevered (pnl_pct = price-based "
         "notional return). No OI, no slippage, no surprise data, no fake OI momentum. "
         "Raw pnl fee=0; `*_after_fees` = Binance taker 0.05%/side (straddle 4 legs). Strategies "
         "identical to v0.1. **Step-1 data verification passed (see verification_report.md).**\n",
         f"## Event universe: {nl.get('CPI',0)} CPI + {nl.get('PPI',0)} PPI = {sum(nl.values())} events "
         "(all events used; none dropped after seeing results).\n",
         "## pre_event_long @ +60m", tbl(pl, cols), "",
         "## pre_event_short @ +60m", tbl(ps, cols), "",
         "## post_event_momentum (entry+1m) @ +60m", tbl(mo, cols), "",
         "## CPI vs PPI divergence (after-fee means at +60m)",
         *verdicts,
         "\n> Per interpretation rules: CPI and PPI are reported separately and NOT merged blindly. "
         "Where one works after fees and the other does not, that is stated above. No thresholds were "
         "tuned to the result; no event was dropped.\n",
         "## Straddle (after 4-leg fees) — most robust per type",
         tbl((agg_df[agg_df.strategy == "straddle"]
              .sort_values(["event_type", "win_rate_afterfees", "worst_value", "mean_afterfees"],
                           ascending=[True, False, False, False]).groupby("event_type").head(1)),
             ["event_type", "config", "n", "mean_afterfees", "win_rate_afterfees", "worst_value",
              "mean_excl_largest_winner"]), "",
         "## Caveats / honesty",
         "- Small n (CPI≈11, PPI≈10). `mean_excl_largest_winner` / `_loser` columns test single-event "
         "dominance; do not claim alpha unless the after-fee mean stays positive AND survives "
         "excluding the biggest winner.",
         "- `realized_max_dd_raw_pct` = additive equity (start 1.0) over events in chronological order.",
         "- Full detail: `event_returns.csv` (returns incl. −10→+120m, both high-low ranges, realized "
         "vol −60→+60m), `pre_event_long/short_results.csv`, `post_event_momentum_results.csv`, "
         "`straddle_grid_results.csv`, `aggregate_by_event_type.csv`."]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
