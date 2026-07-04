"""
scripts/core_events_2025_drawdown_v0_4.py
=========================================

v0.4 — 2025 core-event universe drawdown test. Price-only, cost-free.

Core universe (20): Jackson Hole (1) + 2025 CPI (11) + 2025 FOMC press
conferences (8). NO NFP/PPI/ordinary speeches/surprise/OI/OI-momentum/price
filter/fees/slippage/leverage. Canonical timestamp = open_time_utc.

Goal: compare event-strategy behaviour pre- vs post-May 2025 (drawdown + cum PnL)
across three splits computed SEPARATELY: full_year_2025, pre_may_2025, post_may_2025.

Step-1 verification gates the run; if any event's 1m data is missing it halts and
lists the missing timestamps (no silent dropping).

Returns are UNLEVERED notional. An optional 10%-account curve is also produced:
directional/momentum at 10% gross; straddle at 10% total gross split 5%/5%.
For curves each variant's `event_pnl_pct` is its unlevered return on 100% gross:
directional/momentum = pnl_pct; straddle = (long%+short%)/2 (50/50 of 100% gross).
The 10% curve then applies the spec factor 0.10 * event_pnl_pct uniformly.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "powell_v01", ROOT / "scripts" / "powell_eth_event_backtest_v0_1.py")
v01 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v01)

MAY = pd.Timestamp("2025-05-01", tz="UTC")
ACCT = 0.10  # 10% account scaling factor

# raw 1m sources (real, uploaded across turns)
SOURCES = {
    "powell":  ("data/powell_eth_1m/ETHUSDT-1m-4days_with_utc.csv", "%Y/%m/%d %H:%M"),
    "cpi_ppi": ("data/cpi_ppi_eth_1m/ETHUSDT-1m-cpi_ppi_2025_with_utc.csv", None),
    "fomc":    ("data/fomc_eth_1m/ETHUSDT-1m-fomc_2025_with_utc.csv", None),
}

JH = [("2025-08-22 14:00", "Powell_Jackson_Hole", "JACKSON_HOLE")]
CPI = [(t, n, "CPI") for t, n in [
    ("2025-01-15 13:30", "CPI_Dec2024"), ("2025-02-12 13:30", "CPI_Jan2025"),
    ("2025-03-12 12:30", "CPI_Feb2025"), ("2025-04-10 12:30", "CPI_Mar2025"),
    ("2025-05-13 12:30", "CPI_Apr2025"), ("2025-06-11 12:30", "CPI_May2025"),
    ("2025-07-15 12:30", "CPI_Jun2025"), ("2025-08-12 12:30", "CPI_Jul2025"),
    ("2025-09-11 12:30", "CPI_Aug2025"), ("2025-10-24 12:30", "CPI_Sep2025_Delayed"),
    ("2025-12-18 13:30", "CPI_Nov2025_Delayed")]]
FOMC = [(t, n, "FOMC_PRESS_CONFERENCE") for t, n in [
    ("2025-01-29 19:30", "FOMC_Press_Conference_Jan"), ("2025-03-19 18:30", "FOMC_Press_Conference_Mar"),
    ("2025-05-07 18:30", "FOMC_Press_Conference_May"), ("2025-06-18 18:30", "FOMC_Press_Conference_Jun"),
    ("2025-07-30 18:30", "FOMC_Press_Conference_Jul"), ("2025-09-17 18:30", "FOMC_Press_Conference_Sep"),
    ("2025-10-29 18:30", "FOMC_Press_Conference_Oct"), ("2025-12-10 19:30", "FOMC_Press_Conference_Dec")]]
EVENTS = [(pd.Timestamp(t, tz="UTC"), n, et) for t, n, et in (JH + CPI + FOMC)]
EVENTS.sort(key=lambda x: x[0])

PRIMARY = ["A_pre_long_60", "B_pre_long_120", "C_momentum_60", "D_straddle_TP1.5_SL1.0", "E_best_straddle"]


def load_all():
    fr = []
    for nm, (path, fmt) in SOURCES.items():
        d = pd.read_csv(ROOT / path, encoding="utf-8-sig")
        d["dt"] = (pd.to_datetime(d["open_time_utc"], format=fmt) if fmt
                   else pd.to_datetime(d["open_time_utc"])).dt.tz_localize("UTC")
        fr.append(d[["dt", "open", "high", "low", "close", "volume", "num_trades"]])
    return pd.concat(fr).drop_duplicates("dt").sort_values("dt").reset_index(drop=True).set_index("dt")


def p(df, ev, off, field="open"):
    return v01.price_at(df, ev + timedelta(minutes=off), field)


# ---------------------------------------------------------------------------
# Step 1 verification gate
# ---------------------------------------------------------------------------
def verify(df, out):
    raw = df.reset_index()
    per = raw.groupby(raw["dt"].dt.date).size()
    idx = set(raw["dt"])
    rows, missing = [], []
    for ev, name, et in EVENTS:
        n = int(per.get(ev.date(), 0))
        ok = (n == 1440) and (ev in idx)
        rows.append((name, et, ev, n, ev in idx, ok))
        if not ok:
            missing.append((name, et, ev))
    dup = int(raw["dt"].duplicated().sum())
    allpass = (len(missing) == 0) and (dup == 0)

    L = ["# v0.4 — Step 1 Verification Report\n",
         f"Canonical timestamp: `open_time_utc`. Sources: {', '.join(SOURCES)}.\n",
         f"## RESULT: {'ALL PASS — backtest proceeds' if allpass else 'HALTED — missing data'}\n",
         f"- events checked: {len(EVENTS)}; complete: {len(EVENTS)-len(missing)}; missing: {len(missing)}",
         f"- duplicate open_time_utc across sources: {dup}",
         f"- all present events have 1440 candles & exact timestamp: "
         f"{'yes' if len(missing)==0 else 'NO'}\n",
         "| event_name | type | event_time_utc | candles | ts_exists | ok |",
         "|---|---|---|---|---|---|"]
    for name, et, ev, n, tx, ok in rows:
        L.append(f"| {name} | {et} | {ev:%Y-%m-%d %H:%M} | {n} | {tx} | {'✅' if ok else '❌'} |")
    if missing:
        L += ["", "### MISSING timestamps (halt):"] + [f"- {ev:%Y-%m-%d %H:%M:%S} UTC — {n}" for n, _, ev in missing]
    out.write_text("\n".join(L), encoding="utf-8")
    return allpass


# ---------------------------------------------------------------------------
# per-event raw computations
# ---------------------------------------------------------------------------
def event_returns_row(df, ev, name, et):
    p10, p0 = p(df, ev, -10), p(df, ev, 0)
    def r(a, b): return round((b / a - 1) * 100, 4)
    sp_e60 = v01.window_slice(df, ev, 0, 60); sp_6060 = v01.window_slice(df, ev, 60, 60)
    rets = np.log(sp_6060["close"] / sp_6060["close"].shift(1)).dropna()
    return {
        "event_name": name, "event_type": et, "event_utc": ev.strftime("%Y-%m-%d %H:%M"),
        "may_split": "pre_may_2025" if ev < MAY else "post_may_2025",
        "ret_-10m_to_+15m": r(p10, p(df, ev, 15)), "ret_-10m_to_+30m": r(p10, p(df, ev, 30)),
        "ret_-10m_to_+60m": r(p10, p(df, ev, 60)), "ret_-10m_to_+120m": r(p10, p(df, ev, 120)),
        "ret_event_to_+15m": r(p0, p(df, ev, 15)), "ret_event_to_+30m": r(p0, p(df, ev, 30)),
        "ret_event_to_+60m": r(p0, p(df, ev, 60)),
        "hl_range_event_to_+60m_pct": round((sp_e60["high"].max()-sp_e60["low"].min())/p0*100, 4),
        "hl_range_-60m_to_+60m_pct": round((sp_6060["high"].max()-sp_6060["low"].min())/p0*100, 4),
        "realized_vol_-60_+60_pct": round(float(np.sqrt((rets**2).sum())*100), 4),
    }


def intratrade_mae(df, ev, side, entry_off, exit_off, entry_price):
    span = df.loc[(df.index >= ev+timedelta(minutes=entry_off)) & (df.index <= ev+timedelta(minutes=exit_off))]
    if span.empty or np.isnan(entry_price):
        return np.nan
    if side == "long":
        return round((span["low"].min()/entry_price - 1)*100, 4)
    return round((1 - span["high"].max()/entry_price)*100, 4)


# ---------------------------------------------------------------------------
# equity curve + drawdown for a list of event_pnl_pct (chronological)
# ---------------------------------------------------------------------------
def curve_and_dd(pnls):
    eq_u, eq_a, pk_u, pk_a, dd_u, dd_a = 1.0, 1.0, 1.0, 1.0, 0.0, 0.0
    rows = []
    for epp in pnls:
        eq_u *= (1 + epp/100.0); eq_a *= (1 + ACCT*epp/100.0)
        pk_u = max(pk_u, eq_u); pk_a = max(pk_a, eq_a)
        dd_u = min(dd_u, eq_u/pk_u - 1); dd_a = min(dd_a, eq_a/pk_a - 1)
        rows.append((eq_u, eq_a, pk_u, dd_u*100, dd_a*100))
    return rows, {
        "total_return_unscaled_pct": round((eq_u-1)*100, 4),
        "max_drawdown_unscaled_pct": round(dd_u*100, 4),
        "total_return_10pct_acct_pct": round((eq_a-1)*100, 4),
        "max_drawdown_10pct_acct_pct": round(dd_a*100, 4),
    }


def agg_stats(pnls_by_event):
    s = pd.Series(pnls_by_event, dtype=float).dropna()
    if s.empty:
        return {}
    be, we = s.idxmax(), s.idxmin()
    return {
        "n": int(s.size), "mean": round(s.mean(), 4), "median": round(s.median(), 4),
        "win_rate": round((s > 0).mean(), 4), "best_event": be, "best_value": round(s.max(), 4),
        "worst_event": we, "worst_value": round(s.min(), 4),
        "mean_excl_largest_winner": round(s.drop(be).mean(), 4) if s.size > 1 else np.nan,
        "mean_excl_largest_loser": round(s.drop(we).mean(), 4) if s.size > 1 else np.nan,
    }


# ===========================================================================
def main():
    out = ROOT / "reports" / "core_events_2025_drawdown_v0_4"
    (out / "charts").mkdir(parents=True, exist_ok=True)
    df = load_all()

    if not verify(df, out / "verification_report.md"):
        print("VERIFICATION HALTED — see verification_report.md")
        return
    print("Step 1 verification PASS -> running v0.4")

    # metadata
    meta = pd.DataFrame([{
        "event_date": ev.strftime("%Y-%m-%d"), "event_name": n, "event_type": et,
        "event_time_utc": ev.strftime("%Y-%m-%d %H:%M:%S"),
        "may_split": "pre_may_2025" if ev < MAY else "post_may_2025"} for ev, n, et in EVENTS])
    meta.to_csv(out / "event_metadata_core_2025.csv", index=False)
    print(f"counts: full={len(meta)} pre_may={(meta.may_split=='pre_may_2025').sum()} "
          f"post_may={(meta.may_split=='post_may_2025').sum()}")

    # per-event raw
    ret_rows, trade_rows, str_rows = [], [], []
    per_event = {}   # name -> dict of config -> pnl
    intратrade = {}
    for ev, name, et in EVENTS:
        ret_rows.append(event_returns_row(df, ev, name, et))
        d_long = v01.directional(df, ev, "long", 0.0)
        d_short = v01.directional(df, ev, "short", 0.0)
        mm = v01.momentum(df, ev, 0.0)
        st = v01.straddle(df, ev, 0.0)
        cfg = {}
        for r in d_long:
            cfg[f"pre_long_{r['exit_offset_min']}"] = r["pnl_pct"]
        for r in d_short:
            cfg[f"pre_short_{r['exit_offset_min']}"] = r["pnl_pct"]
        for r in mm["results"]:
            cfg[f"momentum_{r['exit_after_entry_min']}"] = r["pnl_pct"]
        for r in st:
            cfg[f"straddle_TP{r['tp_pct']}_SL{r['sl_pct']}"] = r["combined_pnl_pct"]
            rr = dict(r); rr["event_name"] = name; rr["event_type"] = et
            str_rows.append(rr)
        per_event[name] = cfg
        # intratrade MAE for primary directional/momentum
        e10 = p(df, ev, -10)
        intратrade[name] = {
            "A_pre_long_60": intratrade_mae(df, ev, "long", -10, 60, e10),
            "B_pre_long_120": intratrade_mae(df, ev, "long", -10, 120, e10),
            "C_momentum_60": (intratrade_mae(df, ev, mm["direction"], 1, 61, p(df, ev, 1))),
        }
        v01.make_chart(df, ev, name, out / "charts" / f"{ev:%Y-%m-%d}_{name}.png")

    ret_df = pd.DataFrame(ret_rows)
    ret_df.to_csv(out / "event_returns.csv", index=False)
    str_df = pd.DataFrame(str_rows)
    str_df.to_csv(out / "straddle_grid_results.csv", index=False)

    order = [n for _, n, _ in EVENTS]               # chronological
    types = {n: et for _, n, et in EVENTS}
    split_of = {n: ("pre_may_2025" if ev < MAY else "post_may_2025") for ev, n, _ in EVENTS}

    # choose best straddle combo by full-year unscaled total return (exploratory)
    combos = sorted({k for c in per_event.values() for k in c if k.startswith("straddle_")})
    def straddle_epp(combo, name):  # event_pnl_pct = combined/2 (50/50 of 100% gross)
        return per_event[name].get(combo, np.nan) / 2.0
    best_combo, best_tot = None, -1e9
    for combo in combos:
        pnls = [straddle_epp(combo, n) for n in order if not np.isnan(per_event[n].get(combo, np.nan))]
        _, dd = curve_and_dd(pnls)
        if dd["total_return_unscaled_pct"] > best_tot:
            best_tot, best_combo = dd["total_return_unscaled_pct"], combo
    print(f"best straddle (full-year, exploratory): {best_combo} -> {best_tot:.2f}% unscaled total")

    # event_pnl_pct per primary variant
    def variant_epp(variant, name):
        if variant == "A_pre_long_60":  return per_event[name]["pre_long_60"]
        if variant == "B_pre_long_120": return per_event[name]["pre_long_120"]
        if variant == "C_momentum_60":  return per_event[name]["momentum_60"]
        if variant == "D_straddle_TP1.5_SL1.0": return straddle_epp("straddle_TP1.5_SL1.0", name)
        if variant == "E_best_straddle": return straddle_epp(best_combo, name)
        return np.nan

    # trade log (primary variants)
    for ev, name, et in EVENTS:
        for variant in PRIMARY:
            trade_rows.append({
                "event_name": name, "event_type": et, "event_utc": ev.strftime("%Y-%m-%d %H:%M"),
                "may_split": split_of[name], "variant": variant,
                "event_pnl_pct_unscaled": round(variant_epp(variant, name), 4),
                "intratrade_mae_pct": intратrade[name].get(variant, np.nan),
            })
    pd.DataFrame(trade_rows).to_csv(out / "event_trade_log.csv", index=False)

    # ---- equity curves per split (primary variants) ----
    splits = {"full_year": order,
              "pre_may": [n for n in order if split_of[n] == "pre_may_2025"],
              "post_may": [n for n in order if split_of[n] == "post_may_2025"]}
    dd_split_rows = []
    curve_files = {"full_year": "equity_curve_full_year.csv",
                   "pre_may": "equity_curve_pre_may.csv", "post_may": "equity_curve_post_may.csv"}
    curves_for_plot = {s: {} for s in splits}
    for split, names in splits.items():
        crows = []
        for variant in PRIMARY:
            pnls = [variant_epp(variant, n) for n in names]
            rows, dd = curve_and_dd(pnls)
            mae_series = [intратrade[n].get(variant, np.nan) for n in names]
            worst_mae = np.nanmin(mae_series) if np.any(~np.isnan(mae_series)) else np.nan
            mean_mae = np.nanmean(mae_series) if np.any(~np.isnan(mae_series)) else np.nan
            a = agg_stats({n: variant_epp(variant, n) for n in names})
            dd_split_rows.append({"split": split, "variant": variant, **dd, **a,
                                  "mean_intratrade_mae_pct": None if np.isnan(mean_mae) else round(mean_mae, 4),
                                  "worst_intratrade_mae_pct": None if np.isnan(worst_mae) else round(worst_mae, 4),
                                  "events": "|".join(names)})
            eq_u = [r[0] for r in rows]
            curves_for_plot[split][variant] = eq_u
            for i, n in enumerate(names):
                crows.append({"split": split, "variant": variant, "trade_number": i+1,
                              "event_name": n, "event_type": types[n],
                              "event_pnl_pct": round(pnls[i], 4),
                              "equity_unscaled": round(rows[i][0], 6),
                              "equity_10pct_acct": round(rows[i][1], 6),
                              "rolling_peak_unscaled": round(rows[i][2], 6),
                              "drawdown_unscaled_pct": round(rows[i][3], 4),
                              "drawdown_10pct_acct_pct": round(rows[i][4], 4)})
        pd.DataFrame(crows).to_csv(out / curve_files[split], index=False)
    dd_split_df = pd.DataFrame(dd_split_rows)
    dd_split_df.to_csv(out / "drawdown_summary_by_split.csv", index=False)

    # ---- by event type (full-year): CPI / FOMC / JH / ALL / ALL_excl_JH ----
    groups = {"CPI": [n for n in order if types[n] == "CPI"],
              "FOMC": [n for n in order if types[n] == "FOMC_PRESS_CONFERENCE"],
              "JACKSON_HOLE": [n for n in order if types[n] == "JACKSON_HOLE"],
              "ALL": order, "ALL_excl_JH": [n for n in order if types[n] != "JACKSON_HOLE"]}
    dd_type_rows = []
    for variant in PRIMARY:
        for g, names in groups.items():
            if not names:
                continue
            pnls = [variant_epp(variant, n) for n in names]
            _, dd = curve_and_dd(pnls)
            a = agg_stats({n: variant_epp(variant, n) for n in names})
            dd_type_rows.append({"event_group": g, "variant": variant, **dd, **a})
    dd_type_df = pd.DataFrame(dd_type_rows)
    dd_type_df.to_csv(out / "drawdown_summary_by_event_type.csv", index=False)

    # ---- all variants (directional all exits + momentum + straddle combos) x splits ----
    allv = ([f"pre_long_{e}" for e in v01.DIRECTIONAL_EXITS] +
            [f"pre_short_{e}" for e in v01.DIRECTIONAL_EXITS] +
            [f"momentum_{e}" for e in v01.MOMENTUM_EXITS] + combos)
    allrows = []
    for split, names in splits.items():
        for cfg in allv:
            def epp(n):
                v = per_event[n].get(cfg, np.nan)
                return v/2.0 if cfg.startswith("straddle_") else v
            pnls = [epp(n) for n in names]
            _, dd = curve_and_dd([x for x in pnls if not np.isnan(x)])
            a = agg_stats({n: epp(n) for n in names})
            allrows.append({"split": split, "variant": cfg, **dd, **a})
    pd.DataFrame(allrows).to_csv(out / "strategy_results_all_variants.csv", index=False)

    # ---- equity curve charts ----
    for split, names in splits.items():
        fig, ax = plt.subplots(figsize=(11, 5))
        for variant in PRIMARY:
            eq = curves_for_plot[split][variant]
            ax.plot(range(1, len(eq)+1), eq, marker="o", ms=3, lw=1.2, label=variant)
        ax.axhline(1.0, color="#888", lw=0.8, ls=":")
        ax.set_title(f"v0.4 unscaled equity curve — {split} (n={len(names)})")
        ax.set_xlabel("event # (chronological)"); ax.set_ylabel("equity (start 1.0)")
        ax.legend(fontsize=8); ax.grid(alpha=0.25)
        fig.tight_layout(); fig.savefig(out / "charts" / f"equity_curve_{split}.png", dpi=120); plt.close(fig)

    _summary(out, dd_split_df, dd_type_df, best_combo, meta)

    pd.set_option("display.width", 260); pd.set_option("display.max_columns", None)
    print("\n=== DRAWDOWN BY SPLIT (unscaled) ===")
    print(dd_split_df[["split", "variant", "total_return_unscaled_pct", "max_drawdown_unscaled_pct",
                       "win_rate", "mean", "worst_value", "mean_excl_largest_winner"]].to_string(index=False))
    print("\n=== BY EVENT TYPE (full-year, unscaled) — A_pre_long_60 & D_straddle ===")
    print(dd_type_df[dd_type_df.variant.isin(["A_pre_long_60", "D_straddle_TP1.5_SL1.0"])]
          [["variant", "event_group", "n", "total_return_unscaled_pct", "max_drawdown_unscaled_pct",
            "mean", "win_rate"]].to_string(index=False))
    print(f"\n[out] {out}")


def _summary(out, dd_split, dd_type, best_combo, meta):
    def g(split, variant, col):
        r = dd_split[(dd_split.split == split) & (dd_split.variant == variant)]
        return r[col].iloc[0] if len(r) else float("nan")
    def tbl(df, cols):
        return "\n".join(["| "+" | ".join(cols)+" |", "|"+"|".join(["---"]*len(cols))+"|"] +
                         ["| "+" | ".join(str(r[c]) for c in cols)+" |" for _, r in df.iterrows()])

    A = "A_pre_long_60"; D = "D_straddle_TP1.5_SL1.0"
    fy_ret, fy_dd = g("full_year", A, "total_return_unscaled_pct"), g("full_year", A, "max_drawdown_unscaled_pct")
    pre_ret, pre_dd = g("pre_may", A, "total_return_unscaled_pct"), g("pre_may", A, "max_drawdown_unscaled_pct")
    post_ret, post_dd = g("post_may", A, "total_return_unscaled_pct"), g("post_may", A, "max_drawdown_unscaled_pct")

    # event-type contribution (full-year, A)
    tA = dd_type[dd_type.variant == A].set_index("event_group")
    contrib = {grp: tA.loc[grp, "total_return_unscaled_pct"] for grp in ["CPI", "FOMC_PRESS_CONFERENCE", "JACKSON_HOLE"] if grp in tA.index}
    dominant = max(contrib, key=contrib.get) if contrib else "n/a"
    excl_jh = tA.loc["ALL_excl_JH", "total_return_unscaled_pct"] if "ALL_excl_JH" in tA.index else float("nan")
    all_ret = tA.loc["ALL", "total_return_unscaled_pct"] if "ALL" in tA.index else float("nan")

    pre_exw = g("pre_may", A, "mean_excl_largest_winner")
    post_exw = g("post_may", A, "mean_excl_largest_winner")
    regime_signal = (post_ret > 1.5 * pre_ret) and (pre_exw is not None and pre_exw < 0 <= (post_exw or 0))
    L = ["# v0.4 — 2025 Core-Event Drawdown — Summary\n",
         "**Price-only, cost-free (fee=0, slippage=0, no leverage). 2025 exploratory regime test — "
         "NOT an alpha claim.** Universe: Jackson Hole(1) + CPI(11) + FOMC press conf(8) = 20. "
         "Canonical `open_time_utc`. Step-1 verification passed (see verification_report.md).\n",
         "Headline variant for the split comparison: **A = pre_event_long, exit +60m** (unscaled).\n",
         "## 1-3. Total return & max drawdown by split (variant A, unscaled)",
         "| split | n | total_return % | max_drawdown % |",
         "|---|---|---|---|",
         f"| full_year_2025 | {int((meta.may_split.notna()).sum())} | {fy_ret} | {fy_dd} |",
         f"| pre_may_2025 | {(meta.may_split=='pre_may_2025').sum()} | {pre_ret} | {pre_dd} |",
         f"| post_may_2025 | {(meta.may_split=='post_may_2025').sum()} | {post_ret} | {post_dd} |",
         "",
         f"## 4. Does post-May outperform pre-May? -> "
         f"{'YES' if (post_ret > pre_ret and post_dd >= pre_dd) else 'mixed/needs reading'} "
         f"(post total {post_ret}% vs pre {pre_ret}%; post DD {post_dd}% vs pre DD {pre_dd}%).",
         f"## 5. Still positive excluding Jackson Hole? -> ALL_excl_JH total (variant A) = {excl_jh}% "
         f"vs ALL {all_ret}%.",
         f"## 6. Which event type contributes most (variant A, full-year total return)? -> "
         f"**{dominant}** ({contrib}).",
         f"## 7. Justify an ETH price-regime filter next? -> "
         f"{'likely YES — pre-May edge collapses excluding its top event (pre excl-winner '+str(pre_exw)+'%) while post-May stays positive (post excl-winner '+str(post_exw)+'%)' if regime_signal else 'suggestive but not conclusive from this run'}.\n",
         "## Drawdown by split — all primary variants (unscaled)",
         tbl(dd_split[["split", "variant", "total_return_unscaled_pct", "max_drawdown_unscaled_pct",
                       "total_return_10pct_acct_pct", "max_drawdown_10pct_acct_pct", "win_rate",
                       "worst_value", "mean_excl_largest_winner"]],
             ["split", "variant", "total_return_unscaled_pct", "max_drawdown_unscaled_pct",
              "total_return_10pct_acct_pct", "max_drawdown_10pct_acct_pct", "win_rate",
              "worst_value", "mean_excl_largest_winner"]), "",
         "## By event type (full-year, unscaled)",
         tbl(dd_type[dd_type.variant.isin([A, D])][["variant", "event_group", "n",
             "total_return_unscaled_pct", "max_drawdown_unscaled_pct", "mean", "win_rate",
             "mean_excl_largest_winner"]],
             ["variant", "event_group", "n", "total_return_unscaled_pct", "max_drawdown_unscaled_pct",
              "mean", "win_rate", "mean_excl_largest_winner"]), "",
         f"## Variant E (best straddle by full-year) = **{best_combo}** — EXPLORATORY, not final; "
         "selected on full-year data so it is in-sample and must not be read as alpha.\n",
         "## Interpretation (per rules)",
         "- Drawdowns are computed SEPARATELY per split (curves never mixed). Unscaled = 100% gross "
         "notional; 10%-account = spec 0.10× factor (straddle 5/5).",
         "- If full-year is ok but pre-May is poor and post-May is good, the strategy likely needs an "
         "**ETH price-regime filter** — flagged for a NEXT version; NOT added here.",
         "- `mean_excl_largest_winner` / `_loser` and the ALL_excl_JH row isolate single-event "
         "dominance (esp. Jackson Hole). This does NOT prove alpha; n is small (full 20, pre 6, post 14).",
         "- After-fee columns are intentionally excluded from this cost-free run.",
         "- Note: pre_event_long total return partly rides 2025 directional drift; the straddle "
         "variants are direction-agnostic and a cleaner volatility read."]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
