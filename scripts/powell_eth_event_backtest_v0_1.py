"""
scripts/powell_eth_event_backtest_v0_1.py
=========================================

First raw backtest over the 4 Powell macro event days only.

Scope / guards (per spec):
  * Symbol ETHUSDT, Binance USD-M perpetual, 1m, UTC timestamps.
  * Only the 4 Powell events. NO NFP, NO CPI/PPI/FOMC, NO OI momentum.
  * NO slippage. Fees: raw run uses 0; an optional run applies Binance taker fee.
  * Data comes from the provided 1m CSVs (no live API; offline).

Price convention
----------------
"Price at minute T" = OPEN of the 1m candle whose open_time == T (the price at
the exact minute boundary). Strategy entries/exits fill at the open of the named
minute. Intrabar MFE/MAE and TP/SL use candle high/low.

Data source
-----------
Canonical 1m series is taken from `ETHUSDT-1m-4days_with_utc.csv` using the
`open_time_utc` column (authoritative; the epoch column is lossy scientific
notation). Verified to match `event_checkpoints.csv` exactly (40/40 OHLC).
"""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt    # noqa: E402
import numpy as np                 # noqa: E402
import pandas as pd                # noqa: E402

# ---- fixed config ----------------------------------------------------------
BINANCE_TAKER_FEE = 0.0005   # 0.05% per side (USD-M futures standard taker)
CHECKPOINT_OFFSETS = [-60, -30, -15, -10, 0, 5, 15, 30, 60, 120]  # minutes
DIRECTIONAL_EXITS = [15, 30, 60, 120]      # minutes after event (strat 1 & 2)
MOMENTUM_EXITS = [5, 15, 30, 60]           # minutes after ENTRY (strat 4)
STRADDLE_TPS = [0.5, 1.0, 1.5, 2.0, 3.0]   # percent
STRADDLE_SLS = [0.5, 1.0, 1.5, 2.0]        # percent
STRADDLE_MAX_HOLD_MIN = 120                # exit leftover at +120m if no TP/SL
WINDOWS = {                                 # (pre_min, post_min) event-centered
    "w_180_360": (180, 360),
    "w_60_180": (60, 180),
    "w_15_120": (15, 120),
}

EVENTS = [
    ("2025-06-24", "Powell_Testimony_House", "2025-06-24 14:00"),
    ("2025-08-22", "Jackson_Hole",           "2025-08-22 14:00"),
    ("2025-09-23", "Economic_Outlook",       "2025-09-23 16:35"),
    ("2025-10-14", "NABE",                   "2025-10-14 16:20"),
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_canonical(data_dir: Path) -> pd.DataFrame:
    f = data_dir / "ETHUSDT-1m-4days_with_utc.csv"
    df = pd.read_csv(f, encoding="utf-8-sig")
    df["dt"] = pd.to_datetime(df["open_time_utc"], format="%Y/%m/%d %H:%M").dt.tz_localize("UTC")
    df = df[["dt", "open", "high", "low", "close", "volume", "num_trades"]] \
        .drop_duplicates("dt").sort_values("dt").reset_index(drop=True)
    return df.set_index("dt")


def price_at(df: pd.DataFrame, ts: pd.Timestamp, field="open"):
    """Point-in-time price = `field` of the candle at exactly ts (NaN if absent)."""
    if ts in df.index:
        return float(df.at[ts, field])
    return np.nan


def window_slice(df: pd.DataFrame, event: pd.Timestamp, pre: int, post: int) -> pd.DataFrame:
    lo, hi = event - timedelta(minutes=pre), event + timedelta(minutes=post)
    return df.loc[(df.index >= lo) & (df.index <= hi)].copy()


# ---------------------------------------------------------------------------
# Checkpoints + returns
# ---------------------------------------------------------------------------
def checkpoint_prices(df, event) -> dict:
    return {off: price_at(df, event + timedelta(minutes=off)) for off in CHECKPOINT_OFFSETS}


def event_returns(cp: dict) -> dict:
    p10 = cp[-10]; p0 = cp[0]
    def ret(a, b):
        return np.nan if (a is None or b is None or np.isnan(a) or np.isnan(b)) else (b / a - 1) * 100
    return {
        "ret_-10m_to_+15m": ret(p10, cp[15]),
        "ret_-10m_to_+30m": ret(p10, cp[30]),
        "ret_-10m_to_+60m": ret(p10, cp[60]),
        "ret_event_to_+15m": ret(p0, cp[15]),
        "ret_event_to_+30m": ret(p0, cp[30]),
        "ret_event_to_+60m": ret(p0, cp[60]),
    }


# ---------------------------------------------------------------------------
# Strategy 1 & 2: pre-event directional (enter -10m, exit +N)
# ---------------------------------------------------------------------------
def directional(df, event, side, fee):
    entry = price_at(df, event - timedelta(minutes=10))
    out = []
    for ex in DIRECTIONAL_EXITS:
        px = price_at(df, event + timedelta(minutes=ex))
        if np.isnan(entry) or np.isnan(px):
            raw = np.nan
        else:
            raw = (px / entry - 1) * 100 if side == "long" else (1 - px / entry) * 100
        net = raw - fee * 2 * 100 if not np.isnan(raw) else np.nan  # round-trip taker
        out.append({"exit_offset_min": ex, "entry_price": entry, "exit_price": px,
                    "pnl_pct": None if np.isnan(raw) else round(raw, 6),
                    "pnl_pct_after_fees": None if np.isnan(net) else round(net, 6)})
    return out


# ---------------------------------------------------------------------------
# Strategy 4: post-event momentum (enter at +1m in first-candle direction)
# ---------------------------------------------------------------------------
def momentum(df, event, fee):
    first = df.loc[event] if event in df.index else None
    if first is None:
        return {"direction": None, "entry_price": np.nan, "results": []}
    direction = "long" if first["close"] >= first["open"] else "short"
    entry_ts = event + timedelta(minutes=1)
    entry = price_at(df, entry_ts)
    res = []
    for h in MOMENTUM_EXITS:
        px = price_at(df, entry_ts + timedelta(minutes=h))
        if np.isnan(entry) or np.isnan(px):
            raw = np.nan
        else:
            raw = (px / entry - 1) * 100 if direction == "long" else (1 - px / entry) * 100
        net = raw - fee * 2 * 100 if not np.isnan(raw) else np.nan
        res.append({"exit_after_entry_min": h, "entry_price": entry, "exit_price": px,
                    "pnl_pct": None if np.isnan(raw) else round(raw, 6),
                    "pnl_pct_after_fees": None if np.isnan(net) else round(net, 6)})
    return {"direction": direction, "entry_price": entry,
            "first_candle_open": float(first["open"]), "first_candle_close": float(first["close"]),
            "results": res}


# ---------------------------------------------------------------------------
# Strategy 3: straddle TP/SL grid
# ---------------------------------------------------------------------------
def _leg_exit(span, entry, side, tp_pct, sl_pct):
    """
    Walk a leg bar-by-bar; exit at TP or SL using intrabar high/low.
    Returns (exit_reason, exit_price, mfe_pct, mae_pct, ambiguous).
    Conservative: if a bar touches both TP and SL, assume SL first (adverse-first).
    """
    if side == "long":
        tp = entry * (1 + tp_pct / 100); sl = entry * (1 - sl_pct / 100)
    else:
        tp = entry * (1 - tp_pct / 100); sl = entry * (1 + sl_pct / 100)
    mfe = 0.0; mae = 0.0
    for _, b in span.iterrows():
        hi, lo = b["high"], b["low"]
        # update excursions in % favourable/adverse for this side
        if side == "long":
            mfe = max(mfe, (hi / entry - 1) * 100); mae = min(mae, (lo / entry - 1) * 100)
            hit_tp = hi >= tp; hit_sl = lo <= sl
        else:
            mfe = max(mfe, (1 - lo / entry) * 100); mae = min(mae, (1 - hi / entry) * 100)
            hit_tp = lo <= tp; hit_sl = hi >= sl
        if hit_tp and hit_sl:
            return "sl_ambiguous", sl, mfe, mae, True
        if hit_sl:
            return "sl", sl, mfe, mae, False
        if hit_tp:
            return "tp", tp, mfe, mae, False
    # neither -> exit at last close
    last = span.iloc[-1]["close"]
    return "timeout", float(last), mfe, mae, False


def straddle(df, event, fee):
    entry = price_at(df, event - timedelta(minutes=10))
    span = window_slice(df, event - timedelta(minutes=10),
                        pre=0, post=STRADDLE_MAX_HOLD_MIN + 10)
    span = span.loc[span.index >= event - timedelta(minutes=10)]
    rows = []
    if np.isnan(entry) or span.empty:
        return rows
    for tp in STRADDLE_TPS:
        for sl in STRADDLE_SLS:
            lr, lpx, lmfe, lmae, lamb = _leg_exit(span, entry, "long", tp, sl)
            sr, spx, smfe, smae, samb = _leg_exit(span, entry, "short", tp, sl)
            long_pnl = (lpx / entry - 1) * 100
            short_pnl = (1 - spx / entry) * 100
            combined = long_pnl + short_pnl
            # which side reached its TP first (by exit timestamp) — approximate via reason
            first_side = _which_first(span, entry, tp, sl)
            fee_cost = fee * 4 * 100  # 2 legs * round-trip
            rows.append({
                "event_name": None,  # filled by caller
                "tp_pct": tp, "sl_pct": sl,
                "long_exit_reason": lr, "short_exit_reason": sr,
                "first_side_to_hit": first_side,
                "long_pnl_pct": round(long_pnl, 6), "short_pnl_pct": round(short_pnl, 6),
                "combined_pnl_pct": round(combined, 6),
                "combined_pnl_pct_after_fees": round(combined - fee_cost, 6),
                "long_mfe_pct": round(lmfe, 6), "long_mae_pct": round(lmae, 6),
                "short_mfe_pct": round(smfe, 6), "short_mae_pct": round(smae, 6),
                "ambiguous_bar": bool(lamb or samb),
            })
    return rows


def _which_first(span, entry, tp_pct, sl_pct):
    """Return which side's TP is touched first walking forward (long/short/none/tie)."""
    long_tp = entry * (1 + tp_pct / 100)
    short_tp = entry * (1 - tp_pct / 100)
    for _, b in span.iterrows():
        l = b["high"] >= long_tp
        s = b["low"] <= short_tp
        if l and s:
            return "tie_same_bar"
        if l:
            return "long"
        if s:
            return "short"
    return "none"


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def make_chart(df, event, name, out_png):
    span = window_slice(df, event, 180, 360)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(span.index, span["close"], color="#1f5fbf", lw=1.0)
    ax.axvline(event, color="#cc2a2a", lw=1.5, ls="--", label="event time")
    ax.set_title(f"ETHUSDT 1m — {name}  (event {event:%Y-%m-%d %H:%M} UTC)")
    ax.set_ylabel("price (USDT)")
    ax.set_xlabel("UTC")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=span.index.tz))
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(Path(__file__).resolve().parents[1] / "data" / "powell_eth_1m"))
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parents[1] / "reports" / "powell_v0_1"))
    args = ap.parse_args()
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    (out_dir / "windows").mkdir(parents=True, exist_ok=True)
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    # Raw PnL columns use fee=0; the *_after_fees columns always apply the
    # Binance taker fee, so a single run gives both the raw test and the
    # fee-adjusted variant the spec asks for.
    fee = BINANCE_TAKER_FEE

    df = load_canonical(data_dir)

    cp_rows, ret_rows = [], []
    dir_rows, mom_rows, straddle_rows = [], [], []

    for date, name, ev_str in EVENTS:
        event = pd.Timestamp(ev_str, tz="UTC")
        # --- save 3 cleaned windows ---
        for wname, (pre, post) in WINDOWS.items():
            w = window_slice(df, event, pre, post).reset_index()
            w.rename(columns={"dt": "datetime_utc"}, inplace=True)
            w["datetime_utc"] = w["datetime_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")
            w.to_csv(out_dir / "windows" / f"{date}_{name}_{wname}.csv", index=False)

        # --- checkpoints + returns ---
        cp = checkpoint_prices(df, event)
        rr = event_returns(cp)
        cp_rows.append({"event_date": date, "event_name": name, "event_utc": ev_str,
                        **{f"p_{k:+d}m": (None if np.isnan(v) else round(v, 2)) for k, v in cp.items()}})
        ret_rows.append({"event_date": date, "event_name": name,
                         **{k: (None if np.isnan(v) else round(v, 4)) for k, v in rr.items()}})

        # --- strategies ---
        for side, key in (("long", "strat1_pre_long"), ("short", "strat2_pre_short")):
            for r in directional(df, event, side, fee):
                dir_rows.append({"event_name": name, "strategy": key, "side": side, **r})

        m = momentum(df, event, fee)
        for r in m["results"]:
            mom_rows.append({"event_name": name, "strategy": "strat4_momentum",
                             "direction": m["direction"], "entry_price": m["entry_price"], **r})

        for r in straddle(df, event, fee):
            r["event_name"] = name
            straddle_rows.append(r)

        # --- chart ---
        make_chart(df, event, name, out_dir / "charts" / f"{date}_{name}.png")

    cp_df = pd.DataFrame(cp_rows)
    ret_df = pd.DataFrame(ret_rows)
    dir_df = pd.DataFrame(dir_rows)
    mom_df = pd.DataFrame(mom_rows)
    str_df = pd.DataFrame(straddle_rows)

    cp_df.to_csv(out_dir / "checkpoint_prices.csv", index=False)
    ret_df.to_csv(out_dir / "event_returns.csv", index=False)
    dir_df.to_csv(out_dir / "strategy_directional_pre_event.csv", index=False)
    mom_df.to_csv(out_dir / "strategy_post_event_momentum.csv", index=False)
    str_df.to_csv(out_dir / "strategy_straddle_grid.csv", index=False)

    # ---- console output ----
    pd.set_option("display.width", 240); pd.set_option("display.max_columns", None)
    print("=" * 100); print("CHECKPOINT PRICES (candle open at each offset, UTC)"); print("=" * 100)
    print(cp_df.to_string(index=False))
    print("\n" + "=" * 100); print("EVENT RETURNS (%)"); print("=" * 100)
    print(ret_df.to_string(index=False))
    print("\n" + "=" * 100); print("STRAT 1/2 PRE-EVENT DIRECTIONAL (enter -10m)"); print("=" * 100)
    print(dir_df.pivot_table(index=["event_name", "side"], columns="exit_offset_min",
                             values="pnl_pct").round(4).to_string())
    print("\n" + "=" * 100); print("STRAT 4 POST-EVENT MOMENTUM (enter +1m in 1st-candle direction)"); print("=" * 100)
    print(mom_df.pivot_table(index=["event_name", "direction"], columns="exit_after_entry_min",
                             values="pnl_pct").round(4).to_string())
    print("\n" + "=" * 100); print("STRAT 3 STRADDLE — best combined_pnl_pct per event"); print("=" * 100)
    best = str_df.loc[str_df.groupby("event_name")["combined_pnl_pct"].idxmax()]
    print(best[["event_name", "tp_pct", "sl_pct", "first_side_to_hit",
                "long_exit_reason", "short_exit_reason", "combined_pnl_pct"]].to_string(index=False))

    print(f"\n[out] window CSVs -> {out_dir/'windows'}  (12 files)")
    print(f"[out] charts      -> {out_dir/'charts'}  (4 PNG)")
    print(f"[out] tables      -> {out_dir} (checkpoint_prices, event_returns, 3 strategy CSVs)")
    print(f"[fees] raw PnL uses fee=0; *_after_fees cols apply Binance taker {BINANCE_TAKER_FEE*100:.2f}%/side")


if __name__ == "__main__":
    main()
