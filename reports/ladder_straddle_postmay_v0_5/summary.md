# v0.5 — Ladder-exit 50/50 straddle, post-May 2025 (14 events)

Full position, 50% long + 50% short. Entry = anchor − 1 min. Net of costs (0.10% open + 0.10% close per leg = 0.20% of capital per event; 0.05% fee + 0.05% slippage each side). FOMC tested under press-conf (14:30 ET) and statement (14:00 ET) anchors.

Price treated as continuous: 3% / 5% / 2% / 1% fill at the exact level (detected via 1m high/low); only 'market' exits use the discrete minute price.

## Scenario comparison (14-event portfolio, net)
| scenario | n | cumulative_return_pct | max_drawdown_pct | win_rate | best_event | worst_event | cum_excl_largest_winner_pct | mean_excl_largest_winner_pct |
|---|---|---|---|---|---|---|---|---|
| A_FOMC_press_conf | 14 | -1.1618 | -1.225 | 0.2143 | Powell_Jackson_Hole | CPI_Nov2025_Delayed | -2.0562 | -0.1596 |
| B_FOMC_statement | 14 | -1.6619 | -1.9576 | 0.2857 | Powell_Jackson_Hole | FOMC_Dec | -2.5518 | -0.198 |

## FOMC events: press-conf vs statement (per-event net %)
| event_name | press_conf_net | statement_net |
|---|---|---|
| FOMC_May | -0.2 | -0.2 |
| FOMC_Jun | -0.2 | -0.2 |
| FOMC_Jul | -0.2 | -0.2 |
| FOMC_Sep | -0.2 | 0.3 |
| FOMC_Oct | -0.2 | -0.2 |
| FOMC_Dec | -0.2 | -1.2 |

## Assumptions you may want to correct
- Each leg simulated independently: the leg that breaks out favorably runs the ladder; the opposite leg takes the −1% stop. Both legs can end up stopped on a whipsaw (−1% each).
- Branch-B 3-minute wait is timed from the EVENT minute; branch-A 3-minute wait from the half-sale minute. Remaining-half management starts the candle AFTER the half-sale.
- Same-candle conflicts resolved: −1% stop first, then favorable ladder (5 before 3), then 2%/3% retracement gives, then the market deadline.
- 'Buy 1 minute before' uses the open of the (anchor−1m) candle as entry price.
- n=14 (and only 6 differ between the two FOMC anchors). Single 2025 regime, exploratory — not a statistical edge claim.