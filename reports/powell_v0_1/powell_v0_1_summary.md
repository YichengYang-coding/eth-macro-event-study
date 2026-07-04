# Powell ETH 1m Event Backtest — v0.1 Summary

## Scope / guards
- Symbol **ETHUSDT**, Binance **USD-M perpetual**, **1m**, **UTC** timestamps.
- Only the **4 Powell events**. **No** NFP, **no** CPI/PPI/FOMC, **no** OI momentum.
- **No slippage.** `pnl_pct` uses **fee=0** (raw); `pnl_pct_after_fees` applies **Binance taker 0.05%/side** (round-trip 0.10%).
- Price-at-T = **open of the 1m candle at T**. Canonical series from `ETHUSDT-1m-4days_with_utc.csv` via `open_time_utc`; verified to match `event_checkpoints.csv` exactly (40/40 OHLC).

## Events
| date (UTC) | event | event time (ET) | event time (UTC) |
|---|---|---|---|
| 2025-06-24 | Powell Testimony (House Financial Services) | 10:00 | 14:00 |
| 2025-08-22 | Jackson Hole speech | 10:00 | 14:00 |
| 2025-09-23 | Economic Outlook speech | 12:35 | 16:35 |
| 2025-10-14 | NABE Annual Meeting speech | 12:20 | 16:20 |

## Checkpoint prices (candle open at each offset, UTC)
| event_name | p_-60m | p_-30m | p_-15m | p_-10m | p_+0m | p_+5m | p_+15m | p_+30m | p_+60m | p_+120m |
|---|---|---|---|---|---|---|---|---|---|---|
| Powell_Testimony_House | 2412.65 | 2412.47 | 2417.81 | 2417.64 | 2420.53 | 2427.53 | 2428.09 | 2430.36 | 2429.98 | 2437.0 |
| Jackson_Hole | 4243.34 | 4258.65 | 4300.38 | 4303.98 | 4288.37 | 4428.76 | 4593.54 | 4576.15 | 4611.79 | 4613.93 |
| Economic_Outlook | 4185.99 | 4177.54 | 4182.52 | 4185.6 | 4180.19 | 4168.78 | 4180.0 | 4176.46 | 4163.99 | 4162.45 |
| NABE | 3963.33 | 4039.29 | 4061.18 | 4063.6 | 4099.52 | 4136.81 | 4115.89 | 4135.12 | 4124.0 | 4120.55 |

## Event returns (%)
| event_name | ret_-10m_to_+15m | ret_-10m_to_+30m | ret_-10m_to_+60m | ret_event_to_+15m | ret_event_to_+30m | ret_event_to_+60m |
|---|---|---|---|---|---|---|
| Powell_Testimony_House | 0.4322 | 0.5261 | 0.5104 | 0.3123 | 0.4061 | 0.3904 |
| Jackson_Hole | 6.7277 | 6.3237 | 7.1518 | 7.1162 | 6.7107 | 7.5418 |
| Economic_Outlook | -0.1338 | -0.2184 | -0.5163 | -0.0045 | -0.0892 | -0.3875 |
| NABE | 1.2868 | 1.76 | 1.4864 | 0.3993 | 0.8684 | 0.5971 |

## Strategy 1 & 2 — pre-event directional (enter −10m), raw pnl_pct
| event_name | side | +15m | +30m | +60m | +120m |
|---|---|---|---|---|---|
| Economic_Outlook | long | -0.1338 | -0.2184 | -0.5163 | -0.5531 |
| Economic_Outlook | short | 0.1338 | 0.2184 | 0.5163 | 0.5531 |
| Jackson_Hole | long | 6.7277 | 6.3237 | 7.1518 | 7.2015 |
| Jackson_Hole | short | -6.7277 | -6.3237 | -7.1518 | -7.2015 |
| NABE | long | 1.2868 | 1.76 | 1.4864 | 1.4015 |
| NABE | short | -1.2868 | -1.76 | -1.4864 | -1.4015 |
| Powell_Testimony_House | long | 0.4322 | 0.5261 | 0.5104 | 0.8008 |
| Powell_Testimony_House | short | -0.4322 | -0.5261 | -0.5104 | -0.8008 |

## Strategy 4 — post-event momentum (enter +1m in first-candle direction), raw pnl_pct
| event_name | direction | +5m | +15m | +30m | +60m |
|---|---|---|---|---|---|
| Economic_Outlook | short | 0.1043 | -0.3407 | -0.2213 | 0.3055 |
| Jackson_Hole | long | 1.4797 | 5.2412 | 4.6916 | 5.5836 |
| NABE | long | -0.3418 | -0.3729 | -0.2476 | -0.5247 |
| Powell_Testimony_House | long | 0.3022 | 0.4418 | 0.4377 | 0.4162 |

## Strategy 3 — straddle TP/SL grid (best combined_pnl_pct per event)
| event_name | tp_pct | sl_pct | first_side_to_hit | long_exit_reason | short_exit_reason | combined_pnl_pct | combined_pnl_pct_after_fees |
|---|---|---|---|---|---|---|---|
| Economic_Outlook | 1.0 | 0.5 | short | sl | tp | 0.5 | 0.3 |
| Jackson_Hole | 3.0 | 1.0 | long | tp | sl | 2.0 | 1.8 |
| NABE | 2.0 | 0.5 | long | tp | sl | 1.5 | 1.3 |
| Powell_Testimony_House | 1.5 | 0.5 | long | tp | sl | 1.0 | 0.8 |

- Full 5×4 grid per event in `strategy_straddle_grid.csv` (also long/short MFE/MAE, ambiguous-bar flag).
- TP/SL hits use intrabar high/low; if a single 1m bar touches both a leg's TP and SL, it is flagged `ambiguous_bar` and conservatively treated as **SL-first** (adverse-first). Leftover legs with no TP/SL hit exit at +120m close.

## Read-through (not advice, n=4)
- **Jackson Hole (2025-08-22)** dominates everything: +6–7% over the hour, the only large directional move. A pre-event long or post-event momentum-long captured it; a short was symmetrically hurt.
- The other three are small: Testimony slightly up, NABE moderately up, Economic Outlook a mild fade.
- With only 4 events (one of them an outlier), treat these as **structure/plumbing checks**, not edge estimates.

## OI note (why no OI here)
- This first test deliberately excludes OI. Binance `openInterestHist` supports 30m/1h periods but the official API only returns **recent** history; if we only have daily/24h OI, we must **not** fabricate 30m/60m OI momentum by interpolation. So OI is left out entirely rather than faked.

## Outputs
- `checkpoint_prices.csv`, `event_returns.csv`
- `strategy_directional_pre_event.csv`, `strategy_post_event_momentum.csv`, `strategy_straddle_grid.csv`
- `windows/` — 12 cleaned event-window CSVs (3 per event: −180/+360, −60/+180, −15/+120)
- `charts/` — 4 PNGs (price −180m→+360m, vertical line at event)