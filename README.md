# ETH Macro-Event Reaction Study (2023–2026)

Event-driven research on how ETH (ETHUSDT, Binance USD-M perpetual, 1-minute klines, UTC)
reacts to scheduled U.S. macro releases — **Powell speeches / Jackson Hole, NFP, CPI, PPI,
and FOMC** — culminating in a multi-year **out-of-sample falsification** of the strongest
in-sample signal.

**TL;DR:** the project's headline finding is deliberately *negative and precise*: ETH's
tradeable CPI reaction (a directional edge and an "every CPI breaks out ≥1.5%" volatility
property, including an 11/11 positive TP/SL bracket in 2025) is **regime-conditional, not a
stable structural property**. It fails to replicate in 2023–2024, is only weakly positive in
2026, and its magnitude tracks the prevailing volatility regime. A same-day short control is
negative in every year 2023–2026. One-page summary:
[`reports/resume_summary/ETH_CPI_Event_Study_OnePager.pdf`](reports/resume_summary/ETH_CPI_Event_Study_OnePager.pdf).

---

## Motivation

The original goal was a profitable **2025 news-driven straddle** on ETH: go market-neutral
into scheduled releases and harvest the post-news move. Building it surfaced the key
structural insight that reframed the project: a "straddle" replicated as a **symmetric
long+short on a linear perpetual is net-zero by construction** — unlike an options straddle
it has no long-volatility convexity; it only bleeds fees. So the question became an
**event-reaction study**: which macro events move ETH in a *tradeable (asymmetric)* way, and
is any apparent edge real — or just market beta / a single volatility regime?

## Data & discipline

- **Instrument:** ETHUSDT Binance USD-M perpetual, 1-minute OHLCV, UTC (`open_time_utc`
  canonical). Event-day data spanning 2023–2026.
- **Step-1 verification gates every run:** independent checkpoints reconciled to the raw 1m
  file **100% on OHLCV**, `timestamp == event_time + offset`, 1440 candles per event day, no
  duplicate timestamps. A run **halts** if any event's data is missing — events are never
  silently dropped. Each report directory contains its `verification_report.md`.
- **No post-hoc tuning:** strategy definitions (pre-event long/short, post-event momentum,
  TP/SL bracket grid) and their parameters were fixed before results were inspected; every
  event in scope is reported.
- **Costs modeled explicitly:** Binance taker 0.05%/side (+0.05% slippage where stated);
  bracket strategies charged on all four legs. Aggregates always report
  `mean_excl_largest_winner` to expose single-event dependence.
- **Raw exchange data is not redistributed** in this repo (licensing); scripts, per-event
  results, verification reports, and charts are included so every number can be traced.

## Repo structure

```
scripts/                                  # analysis code (chronological versions)
  powell_eth_event_backtest_v0_1.py       # core framework: loaders, verification,
                                          #   directional / momentum / TP-SL bracket grid
  powell_eth_event_analysis_v0_2.py       # Powell deep-dive (phase decomposition, excl-JH)
  eth_event_backtest_v0_2_powell_nfp.py   # + NFP universe
  cpi_ppi_event_backtest_v0_3a.py         # CPI vs PPI screening (the pivotal run)
  core_events_2025_drawdown_v0_4.py       # 20-event portfolio: equity curves, DD, Sharpe
  fomc_statement_vs_pressconf_v0_4b.py    # FOMC statement (14:00 ET) vs press conf (14:30 ET)
  ladder_straddle_postmay_v0_5.py         # custom ladder-exit two-leg strategy
reports/
  powell_v0_1/, powell_v0_2/              # Powell events: only Jackson Hole matters
  powell_nfp_v0_2/                        # NFP: reactions too small to clear fees
  cpi_ppi_v0_3a/                          # CPI works, PPI whipsaws  ← key screening result
  core_events_2025_drawdown_v0_4/         # portfolio view, pre-May vs post-May splits
  fomc_statement_vs_pressconf_v0_4b/      # the two FOMC anchors carry opposite signals
  ladder_straddle_postmay_v0_5/           # ladder exit: net negative, Jackson-Hole-driven
  cpi_oos_2023_2024_results.csv           # OOS falsification: CPI long, 24 events
  cpi_2026_oos_results.csv                # OOS 2026: long / short / bracket, 6 events
  cpi_straddle_oos_2023_2024.csv          # OOS falsification: TP/SL bracket
  v0_1_research_log.md                    # early research log
  resume_summary/                         # one-page PDF + markdown source
```

## What each stage found

| Stage | Question | Result |
|---|---|---|
| v0.1–v0.2 (Powell, NFP) | Do Fed speeches / NFP move ETH tradeably? | Only **Jackson Hole**; ordinary speeches nothing; NFP moves too small to clear fees. |
| v0.3a (CPI vs PPI) | Same footing comparison | **CPI reacts cleanly** (11/11 events broke ≥1.5%, no whipsaw); **PPI whipsaws** (3 double-stops). CPI becomes the focus. |
| v0.4 (20-event portfolio) | Portfolio behavior, pre- vs post-May 2025 | Full-year +16.3% unscaled / −4.55% maxDD; post-May ≫ pre-May (pre-May turns negative ex-largest-winner); **CPI dominates, FOMC pre-long detracts**. |
| v0.4b (FOMC anchors) | Statement vs press conference | Opposite signals: statement → fade works; press conf → momentum works (n=8, exploratory). |
| v0.5 (ladder exit) | Does a ladder TP rescue the two-leg trade? | **No** — net negative on both anchors; every positive cell traces to Jackson Hole alone. |
| OOS (2023–24, 2026) | Does the CPI result replicate? | **No (2023–24)** — long: +0.06% mean, median −0.27%, 42% win; bracket: 15/24. **Weakly (2026)** — long +0.38%, 67%; bracket 4/6. Short control negative **every year 2023–2026**. Robust across +15/30/60/120m exits. |

## Final conclusion

ETH's tradeable CPI reaction is **regime-conditional**: its magnitude tracks the prevailing
volatility regime monotonically (2023–24 ≈ 0 → 2026 weak → 2025 strong) and holds across
exit horizons, while the short side is negative in every year — i.e. CPI drives a
*directionally upward-biased reaction whose size depends on the regime*, not two-sided noise
and **not universal alpha**. The post-May 2025 split was an ex-ante regime call; the
2023–2024 and 2026 windows were run to *test* that call, and the result is reported as-is.

## Honest limitations

- Small n throughout (CPI 11/year, FOMC 8, Jackson Hole 1); single-asset; 1m OHLCV only, so
  intrabar sequencing is unknown and bracket same-bar TP+SL cases are resolved conservatively
  (stop-first).
- No order-book depth, funding, or liquidation modeling; fills assumed at candle open.
- "Best" bracket combos and the FOMC anchor split are exploratory (in-sample); they are
  reported with per-event detail rather than claimed as edges.
- This is research output, **not** a deployable strategy — capacity in a ±10-minute event
  window on 1m depth is tiny, and the out-of-sample evidence is precisely why the 2025
  numbers should not be extrapolated.

## Reproducing

Scripts run on Python 3 with `pandas`, `numpy`, `matplotlib`. Each script expects the
corresponding Binance USD-M 1m event-day CSVs under `data/` (column layout:
`open_time_utc, open, high, low, close, volume[, num_trades]`; one file per event universe —
see the `SOURCES` dict at the top of each script). Obtain klines from Binance (e.g.
https://data.binance.vision) and every script will first run Step-1 verification and refuse
to proceed unless the data reconciles.
