# Powell ETH 1m — v0.2 Analysis Summary

Built on v0.1 (same data/guards: no NFP, no CPI/PPI/FOMC, no OI, no slippage). Raw PnL uses fee=0; `*_after_fees` apply Binance taker 0.05%/side; straddle fees are charged on **four legs** (2 entries + 2 exits = 0.20%).

## 1. Phase decomposition (%)
| event_name | event_utc | pre_event_drift_-60_to_event | immediate_reaction_event_to_+15 | post_event_continuation_+15_to_+60 | full_event_move_-10_to_+60 |
|---|---|---|---|---|---|
| Powell_Testimony_House | 2025-06-24 14:00 | 0.3266 | 0.3123 | 0.0778 | 0.5104 |
| Jackson_Hole | 2025-08-22 14:00 | 1.0612 | 7.1162 | 0.3973 | 7.1518 |
| Economic_Outlook | 2025-09-23 16:35 | -0.1386 | -0.0045 | -0.383 | -0.5163 |
| NABE | 2025-10-14 16:20 | 3.4363 | 0.3993 | 0.197 | 1.4864 |

## 3. Excursions over [-180m,+360m] (anchored at event-time price)
| event_name | event_utc | event_anchor_price | max_up_180_360_pct | max_down_180_360_pct | max_1m_high_low_range | max_1m_range_time_utc | biggest_move_segment | biggest_move_segment_range |
|---|---|---|---|---|---|---|---|---|
| Powell_Testimony_House | 2025-06-24 14:00 | 2420.53 | 2.5098 | -0.9952 | 30.14 | 2025-06-24 16:43 | +180..+360 | 64.27 |
| Jackson_Hole | 2025-08-22 14:00 | 4288.37 | 13.2831 | -1.9208 | 99.24 | 2025-08-22 14:00 | 0..+15 | 337.28 |
| Economic_Outlook | 2025-09-23 16:35 | 4180.19 | 0.7067 | -1.0734 | 14.72 | 2025-09-23 14:34 | +180..+360 | 52.41 |
| NABE | 2025-10-14 16:20 | 4099.52 | 1.5546 | -5.1077 | 65.0 | 2025-10-14 16:20 | -60..0 | 204.46 |

## 2. Excluding Jackson Hole — is the edge one event?
| metric | avg_all_4 | avg_excl_JH | JH_only |
|---|---|---|---|
| pre_event_long_exit+15m | 2.0782 | 0.5284 | 6.7277 |
| pre_event_long_exit+30m | 2.0979 | 0.6893 | 6.3237 |
| pre_event_long_exit+60m | 2.1581 | 0.4935 | 7.1518 |
| pre_event_long_exit+120m | 2.2127 | 0.5497 | 7.2015 |
| momentum_entry+1m_exit+15m | 1.2423 | -0.0906 | 5.2412 |
| momentum_entry+1m_exit+30m | 1.1651 | -0.0104 | 4.6916 |
| momentum_entry+1m_exit+60m | 1.4451 | 0.0657 | 5.5836 |
| straddle_TP1.0_SL1.0_afterfees | -0.2 | -0.2 | -0.2 |
| straddle_TP1.5_SL1.0_afterfees | 0.0899 | 0.0199 | 0.3 |
| straddle_TP2.0_SL1.0_afterfees | 0.1952 | -0.0064 | 0.8 |

> If `avg_excl_JH` collapses toward ~0 or negative while `avg_all_4` is positive, the result is carried by Jackson Hole alone.

## 4. Straddle robustness (most robust, not highest return)
- **Most robust combo: TP1.5/SL1.0** — profitable on 3/4 events, worst-event -0.5404%, mean 0.0899%, mean excl-JH 0.0199%.
- Robustness ranking = (#events profitable after fees) → (best worst-case) → (highest mean). Per-combo per-event PnL and an `only_profitable_on_jackson_hole` flag are in `straddle_robustness.csv` / `strategy_straddle_grid` (v0.1).

## 5. Momentum entry-timing
Entry +1m/+3m/+5m × exit +15/+30/+60m in `momentum_entry_timing.csv` (direction from the first 1m candle).

## 6. final_summary.csv
| event_name | event_time_utc | pre_60_to_event_return | event_to_15_return | event_to_60_return | minus10_to_60_return | max_up_180_360 | max_down_180_360 | best_directional_strategy | best_straddle_setting |
|---|---|---|---|---|---|---|---|---|---|
| Powell_Testimony_House | 2025-06-24 14:00 | 0.3266 | 0.3123 | 0.3904 | 0.5104 | 2.5098 | -0.9952 | pre_long@+60m (+0.5104%) | TP1.5/SL0.5 |
| Jackson_Hole | 2025-08-22 14:00 | 1.0612 | 7.1162 | 7.5418 | 7.1518 | 13.2831 | -1.9208 | pre_long@+60m (+7.1518%) | TP3.0/SL1.0 |
| Economic_Outlook | 2025-09-23 16:35 | -0.1386 | -0.0045 | -0.3875 | -0.5163 | 0.7067 | -1.0734 | pre_short@+60m (+0.5163%) | TP1.0/SL0.5 |
| NABE | 2025-10-14 16:20 | 3.4363 | 0.3993 | 0.5971 | 1.4864 | 1.5546 | -5.1077 | pre_long@+60m (+1.4864%) | TP2.0/SL0.5 |

## Caveat
n=4 with one outlier (Jackson Hole). The excluding-JH block is the key robustness lens; everything else is structure, not an edge estimate.