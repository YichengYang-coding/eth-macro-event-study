# v0.4b — FOMC: Statement (14:00 ET) vs Press-Conference (14:30 ET)

FOMC-only (8 events). No CPI, no Jackson Hole, no OI, no fees, no slippage. Price-only, unlevered. Entry −10m; exits +15/+30/+60/+120m (momentum entry+1m, exits +5/+15/+30/+60m). Cumulative = compounded chronological equity (start 1.0). Straddle metric = combined_pnl_pct.

## Key configs — A (statement) vs B (press-conf)
| config | A cum% | A maxDD% | A win | A exclWin | B cum% | B maxDD% | B win | B exclWin |
|---|---|---|---|---|---|---|---|---|
| pre_long +60m | -4.4884 | -5.8927 | 0.25 | -0.8376 | -0.6545 | -3.9135 | 0.375 | -0.5213 |
| pre_long +120m | -4.2051 | -5.2104 | 0.5 | -0.6903 | 0.9729 | -2.7174 | 0.5 | -0.2321 |
| pre_short +60m | 4.5812 | -1.4879 | 0.75 | 0.3317 | 0.4723 | -3.0849 | 0.625 | -0.2445 |
| momentum +60m | -2.4858 | -3.9525 | 0.375 | -0.6253 | 8.0328 | -0.3043 | 0.875 | 0.6786 |
| straddle TP1.5/SL1.0 | 1.88 | -1.1236 | 0.75 | 0.1962 | -0.2639 | -2.0 | 0.5 | -0.1055 |

## Best straddle combo (by cumulative) — A: **straddle_TP2.0_SL1.5** (2.5178%), B: **straddle_TP3.0_SL0.5** (3.716%) — exploratory (in-sample), not alpha.

## Notes
- n=8 per anchor — tiny sample, 2025 only; structure/plumbing, not an edge claim.
- Statement (14:00) and press-conf (14:30) windows overlap heavily; the 30-min shift mainly changes which minute is the 'ignition' candle and whether the entry sits before the statement or between statement and presser.
- `mean_excl_largest_winner` isolates single-event dominance. After-fee not shown (cost-free run).
- Full detail: `aggregate_by_anchor_all_configs.csv`, `straddle_grid_comparison.csv`, `directional/momentum/straddle_*_by_anchor.csv`, `event_returns_by_anchor.csv`.