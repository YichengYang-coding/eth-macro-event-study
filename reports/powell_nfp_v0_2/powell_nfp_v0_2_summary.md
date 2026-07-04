# ETH 1m Event Backtest — v0.2 (Powell + 2025 NFP)

**2025 exploratory regime test — NOT a statistical edge claim.** Phase-specific to the 2025 crypto regime; not extended to 2021-2024.

Guards: no CPI/PPI/FOMC, no OI, no slippage. Raw pnl uses fee=0; `*_after_fees` apply Binance taker 0.05%/side (straddle on 4 legs). Strategies identical to v0.1. Checkpoints verified to match raw 1m 100% (121/121 OHLCV).

## Event universe (15)
- Powell (4): Testimony 06-24, Jackson Hole 08-22, Economic Outlook 09-23, NABE 10-14.
- NFP (11): the actual 2025 Employment Situation releases; 10-03 and 11-07 excluded (no report released). Sep & Nov reports were delayed (released 11-20 and 12-16).

## pre_event_long @ +60m (raw pnl_pct) — Powell / NFP / combined
| group | n | mean | median | win_rate | best_event | worst_event | mean_excl_largest_winner | mean_excl_largest_loser | mean_afterfees |
|---|---|---|---|---|---|---|---|---|---|
| Powell | 4 | 2.1581 | 0.9984 | 0.75 | Jackson_Hole | Economic_Outlook | 0.4935 | 3.0495 | 2.0581 |
| NFP | 11 | 0.0669 | 0.1401 | 0.5455 | NFP_Jan2025 | NFP_Dec2024 | -0.0853 | 0.1812 | -0.0331 |
| ALL | 15 | 0.6245 | 0.2185 | 0.6 | Jackson_Hole | NFP_Dec2024 | 0.1583 | 0.746 | 0.5245 |

## momentum entry+1m @ +60m (raw pnl_pct)
| group | n | mean | median | win_rate | best_event | worst_event | mean_excl_largest_winner | mean_excl_largest_loser | mean_afterfees |
|---|---|---|---|---|---|---|---|---|---|
| Powell | 4 | 1.4451 | 0.3608 | 0.75 | Jackson_Hole | NABE | 0.0657 | 2.1018 | 1.3451 |
| NFP | 11 | -0.2639 | -0.4082 | 0.2727 | NFP_Jan2025 | NFP_Feb2025 | -0.4024 | -0.1566 | -0.3639 |
| ALL | 15 | 0.1918 | -0.3029 | 0.4 | Jackson_Hole | NFP_Feb2025 | -0.1933 | 0.301 | 0.0918 |

## Most robust straddle per group (after 4-leg fees; robust = #profitable → worst-case → mean)
| group | tp_pct | sl_pct | n | mean | median | win_rate | worst_value | mean_excl_largest_winner |
|---|---|---|---|---|---|---|---|---|
| ALL | 1.5 | 1.0 | 15 | -0.2894 | 0.3 | 0.6667 | -2.2 | -0.3315 |
| NFP | 1.5 | 1.0 | 11 | -0.4273 | 0.3 | 0.6364 | -2.2 | -0.5 |
| Powell | 1.5 | 1.0 | 4 | 0.0899 | 0.3 | 0.75 | -0.5404 | 0.0199 |

## Notes
- `excluding largest winner / loser` columns isolate single-event dominance.
- Full per-event detail: `event_returns.csv` (incl. high-low ranges event→+60m and −60→+60m, and realized vol −60→+60m from 1m log returns), `strategy_*` CSVs, and the `aggregate_*` CSVs for every config × group.
- n is small (Powell=4, NFP=11). Treat as structure/plumbing, not edge.