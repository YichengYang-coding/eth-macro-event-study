# v0.3a — CPI/PPI 2025 Event-Reaction Backtest — Summary

**2025 exploratory regime test — NOT a statistical edge claim. Price-only.**
ETHUSDT Binance USD-M perpetual, 1m, historical, UTC. Unlevered (pnl_pct = price-based notional return). No OI, no slippage, no surprise data, no fake OI momentum. Raw pnl fee=0; `*_after_fees` = Binance taker 0.05%/side (straddle 4 legs). Strategies identical to v0.1. **Step-1 data verification passed (see verification_report.md).**

## Event universe: 11 CPI + 10 PPI = 21 events (all events used; none dropped after seeing results).

## pre_event_long @ +60m
| event_type | n | mean_raw | median_raw | win_rate_raw | best_event | worst_event | mean_excl_largest_winner | mean_excl_largest_loser | mean_afterfees | realized_max_dd_raw_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| CPI | 11 | 0.8236 | 1.6695 | 0.6364 | CPI_Jul2025 | CPI_Jan2025 | 0.5815 | 1.1939 | 0.7236 | -3.8805 |
| PPI | 10 | -0.1693 | 0.236 | 0.5 | PPI_Dec2024 | PPI_Jul2025 | -0.2945 | 0.2479 | -0.2693 | -3.8483 |
| ALL | 21 | 0.3508 | 0.5748 | 0.5714 | CPI_Jul2025 | PPI_Jul2025 | 0.2061 | 0.5645 | 0.2508 | -4.543 |

## pre_event_short @ +60m
| event_type | n | mean_raw | median_raw | win_rate_raw | best_event | worst_event | mean_excl_largest_winner | mean_excl_largest_loser | mean_afterfees | realized_max_dd_raw_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| CPI | 11 | -0.8236 | -1.6695 | 0.3636 | CPI_Jan2025 | CPI_Jul2025 | -1.1939 | -0.5815 | -0.9236 | -10.4271 |
| PPI | 10 | 0.1693 | -0.236 | 0.5 | PPI_Jul2025 | PPI_Dec2024 | -0.2479 | 0.2945 | 0.0693 | -1.9626 |
| ALL | 21 | -0.3508 | -0.5748 | 0.4286 | PPI_Jul2025 | CPI_Jul2025 | -0.5645 | -0.2061 | -0.4508 | -10.0863 |

## post_event_momentum (entry+1m) @ +60m
| event_type | n | mean_raw | median_raw | win_rate_raw | best_event | worst_event | mean_excl_largest_winner | mean_excl_largest_loser | mean_afterfees | realized_max_dd_raw_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| CPI | 11 | 0.4701 | 0.853 | 0.6364 | CPI_Jan2025 | CPI_Feb2025 | 0.2992 | 0.678 | 0.3701 | -3.0679 |
| PPI | 10 | 0.1787 | -0.0874 | 0.4 | PPI_Jul2025 | PPI_Sep2025_Delayed | -0.146 | 0.3067 | 0.0787 | -1.2586 |
| ALL | 21 | 0.3314 | 0.0831 | 0.5238 | PPI_Jul2025 | CPI_Feb2025 | 0.1929 | 0.4284 | 0.2314 | -3.2383 |

## CPI vs PPI divergence (after-fee means at +60m)
- **pre_event_long@+60m** after fees: CPI +0.7236% vs PPI -0.2693% -> CPI≥0, PPI<0
- **pre_event_short@+60m** after fees: CPI -0.9236% vs PPI +0.0693% -> PPI≥0, CPI<0
- **post_event_momentum@+60m** after fees: CPI +0.3701% vs PPI +0.0787% -> both≥0

> Per interpretation rules: CPI and PPI are reported separately and NOT merged blindly. Where one works after fees and the other does not, that is stated above. No thresholds were tuned to the result; no event was dropped.

## Straddle (after 4-leg fees) — most robust per type
| event_type | config | n | mean_afterfees | win_rate_afterfees | worst_value | mean_excl_largest_winner |
|---|---|---|---|---|---|---|
| ALL | TP1.5/SL1.0 | 21 | -0.0571 | 0.8571 | -2.0 | 0.125 |
| CPI | TP1.5/SL1.0 | 11 | 0.3 | 1.0 | 0.5 | 0.5 |
| PPI | TP1.0/SL0.5 | 10 | 0.0 | 0.8 | -1.0 | 0.1667 |

## Caveats / honesty
- Small n (CPI≈11, PPI≈10). `mean_excl_largest_winner` / `_loser` columns test single-event dominance; do not claim alpha unless the after-fee mean stays positive AND survives excluding the biggest winner.
- `realized_max_dd_raw_pct` = additive equity (start 1.0) over events in chronological order.
- Full detail: `event_returns.csv` (returns incl. −10→+120m, both high-low ranges, realized vol −60→+60m), `pre_event_long/short_results.csv`, `post_event_momentum_results.csv`, `straddle_grid_results.csv`, `aggregate_by_event_type.csv`.