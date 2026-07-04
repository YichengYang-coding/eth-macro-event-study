# ETH Macro-Event Reaction Study — One-Page Research Summary

**Asset/Data:** ETHUSDT Binance USD-M perpetual, 1-minute klines, UTC. Event-day data spanning
**2023–2026** (Powell/Jackson Hole, NFP, CPI, PPI, FOMC). Built and run in a cost-aware,
leakage-controlled backtest framework.

## Motivation
My original goal was to build a profitable **2025 news-driven (macro-event) straddle** on ETH
for a trading-firm application — go market-neutral into scheduled releases and harvest the
post-news move. Building it surfaced a key insight: a "straddle" replicated with a **symmetric
long+short position on a *linear* perpetual is net-zero by construction** (the two legs cancel
their own P&L and the position only bleeds fees) — unlike an *options* straddle, it has no long-
volatility convexity. That realization reframed the project: rather than force a winning
symmetric straddle, I turned it into a disciplined **event-reaction study** — which macro events
move ETH in a *tradeable* (asymmetric) way, and whether any edge is real or just market beta /
a single volatility regime. The asymmetric variants (ladder TP/SL, directional, momentum) were
my attempt to turn that net-zero structure into something with an actual payoff.

## Framework & data discipline
- Canonical UTC timestamp (`open_time_utc`); mandatory **Step-1 verification before every run**:
  checkpoints reconciled to raw 1m **100% on OHLCV**, `timestamp == event_time + offset`,
  1440 candles/day, no duplicates. Runs **halt** on any missing event — never silently drop.
- Strategies fixed up front (pre-event long/short, post-event momentum, TP/SL straddle grid);
  no threshold tuning to fit results; fees/slippage modeled explicitly (0.05% fee + 0.05% slip).

## Event screening (2025)
Compared all event types on one footing and **screened out the noise**:
- **PPI**: no tradeable reaction (whipsaw double-stops). **FOMC pre-long**: negative contributor.
- **Ordinary Powell/Fed speeches**: nothing. **Jackson Hole**: large but a single event.
- **CPI**: cleanest, broad-based reaction → became the focus.

## 2025 finding (in-sample)
CPI pre-event long (enter −10m, exit +60m), post-May 2025, net of 0.2%/trade:
**+9.5% cumulative, −1.08% max drawdown, 86% win (6/7)**. A direction-neutral
**path-dependent TP/SL bracket** (TP +1.5% / SL −1.0% per leg): **11/11 positive after
4-leg fees**. *Note: a static symmetric long+short on a linear perp has no convexity and is
net-zero; this positive result comes entirely from the path-dependent TP/SL execution, not
from holding a true static straddle.*

## Multi-layer validation (the core of the work)
| Test | 2025 (in-sample) | Out-of-sample / control | Verdict |
|---|---|---|---|
| Non-event-day baseline | CPI long mean at **97.5th pct** of random 60-min holds | random non-CPI holds avg **−0.16%** | **not pure beta** |
| CPI long, **2023–2024 OOS** | +9.5% (post-May) | **+0.06% mean, median −0.27%, 42% win** | does NOT replicate |
| CPI long, **2026 OOS** | +9.5% (post-May) | **+0.38% mean, 67% win (4/6)** | partial — weak-positive |
| Path-dependent TP/SL bracket, **2023–24 / 2026 OOS** | 11/11 positive | **15/24 / 4/6** | does NOT fully replicate |
| Same-day **short** control | −11% | 2023 −, 2024 −, **2026 −4.6% (0/6)** | **negative every year, 2023–2026** |
| Robustness across exit horizons | +15/+30/+60/+120m all positive | OOS all ≈0 / median negative | edge **not** an exit-time artifact |

**Regime gradient (the key pattern).** CPI long directional return tracks the prevailing
volatility regime monotonically: **2023–24 ≈0 → 2026 weak-positive (+0.38%) → 2025 strong
(+1.31%/event)**. The effect strengthens with the regime rather than appearing/vanishing
randomly — itself evidence the dependence is on regime, not on a single lucky year. *The
post-May split was an **ex-ante regime call** (ETH entering a higher-volatility, higher-
participation phase after reclaiming ~½ of its prior high), not a PnL-optimized cut — the
2023–24 and 2026 controls were run precisely to test, not flatter, that call.*

## Final, falsifiable conclusion
ETH's tradeable reaction to CPI — both the directional edge and the "always ≥1.5% breakout"
volatility property — is **regime-conditional, not a stable structural property of ETH-vs-CPI.**
The directional edge **scales with the volatility regime** (≈0 in 2023–24, weak in 2026, strong
in 2025) and holds across all exit horizons, while the **short side is negative in every year
2023–2026** — so CPI drives a *directionally upward-biased reaction whose magnitude depends on
the regime*, not two-sided noise. The headline 2025 result is a genuine regime effect, **not
universal alpha** — established by explicit multi-year out-of-sample falsification rather than
in-sample curve-fitting.

## Anticipated questions & defense
- **"Isn't post-May 2025 cherry-picked?"** — Post-May was an *ex-ante regime call* (ETH entering
a higher-volatility / higher-participation phase), **not** a PnL-optimized cut. The 2023–24 and
2026 out-of-sample windows were run to *test* that call; the result (effect is regime-dependent,
not universal) is reported as-is.
- **"You said a symmetric straddle is net-zero, yet the bracket is 11/11 positive — contradiction?"**
— No: the static symmetric long+short has **no convexity** and is net-zero by construction. The
positive result comes from **path-dependent TP/SL execution** (asymmetric exits), not from holding
a true static straddle. (Renamed accordingly: *path-dependent TP/SL bracket*, not "straddle.")
- **"Isn't the short-side result just crypto risk-on / long-run beta?"** — This **does not claim a
stable standalone alpha**. It shows CPI reaction days carry a **directional asymmetry** relative to
(a) random non-event 60-min holds and (b) same-day short controls — a *characterization of event
behavior*, not an alpha claim.

## Skills demonstrated
Event-study design; rigorous data integrity/verification; leakage control; cost/slippage
modeling; alpha-vs-beta separation via baselines and directional controls; **out-of-sample
falsification**; honest characterization of edge boundaries and single-event/regime dependence.
