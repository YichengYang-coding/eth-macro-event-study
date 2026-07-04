# v0.4 — 2025 Core-Event Drawdown — Summary

**Price-only, cost-free (fee=0, slippage=0, no leverage). 2025 exploratory regime test — NOT an alpha claim.** Universe: Jackson Hole(1) + CPI(11) + FOMC press conf(8) = 20. Canonical `open_time_utc`. Step-1 verification passed (see verification_report.md).

Headline variant for the split comparison: **A = pre_event_long, exit +60m** (unscaled).

## 1-3. Total return & max drawdown by split (variant A, unscaled)
| split | n | total_return % | max_drawdown % |
|---|---|---|---|
| full_year_2025 | 20 | 16.3044 | -4.5474 |
| pre_may_2025 | 6 | 1.3911 | -3.9936 |
| post_may_2025 | 14 | 14.7087 | -2.276 |

## 4. Does post-May outperform pre-May? -> YES (post total 14.7087% vs pre 1.3911%; post DD -2.276% vs pre DD -3.9936%).
## 5. Still positive excluding Jackson Hole? -> ALL_excl_JH total (variant A) = 8.5417% vs ALL 16.3044%.
## 6. Which event type contributes most (variant A, full-year total return)? -> **CPI** ({'CPI': np.float64(9.2568), 'JACKSON_HOLE': np.float64(7.1518)}).
## 7. Justify an ETH price-regime filter next? -> likely YES — pre-May edge collapses excluding its top event (pre excl-winner -0.3163%) while post-May stays positive (post excl-winner 0.5378%).

## Drawdown by split — all primary variants (unscaled)
| split | variant | total_return_unscaled_pct | max_drawdown_unscaled_pct | total_return_10pct_acct_pct | max_drawdown_10pct_acct_pct | win_rate | worst_value | mean_excl_largest_winner |
|---|---|---|---|---|---|---|---|---|
| full_year | A_pre_long_60 | 16.3044 | -4.5474 | 1.5713 | -0.4601 | 0.55 | -2.88 | 0.4471 |
| full_year | B_pre_long_120 | 18.6954 | -5.1166 | 1.7863 | -0.5185 | 0.55 | -1.9688 | 0.5562 |
| full_year | C_momentum_60 | 19.9916 | -2.9437 | 1.8703 | -0.2961 | 0.75 | -1.6089 | 0.6832 |
| full_year | D_straddle_TP1.5_SL1.0 | 2.9122 | -1.0 | 0.2884 | -0.1 | 0.8 | -1.0 | 0.1385 |
| full_year | E_best_straddle | 5.6797 | -1.985 | 0.5607 | -0.1999 | 0.5 | -0.5 | 0.2289 |
| pre_may | A_pre_long_60 | 1.3911 | -3.9936 | 0.1492 | -0.4026 | 0.3333 | -2.88 | -0.3163 |
| pre_may | B_pre_long_120 | 1.9988 | -4.7623 | 0.2147 | -0.4815 | 0.5 | -1.9688 | -0.4322 |
| pre_may | C_momentum_60 | 3.0774 | -2.9437 | 0.3124 | -0.2961 | 0.6667 | -1.6089 | 0.014 |
| pre_may | D_straddle_TP1.5_SL1.0 | 1.1354 | -0.1193 | 0.1131 | -0.0119 | 0.8333 | -0.1193 | 0.1761 |
| pre_may | E_best_straddle | 1.1175 | -1.3638 | 0.1129 | -0.1369 | 0.5 | -0.5 | -0.0239 |
| post_may | A_pre_long_60 | 14.7087 | -2.276 | 1.42 | -0.2276 | 0.6429 | -2.276 | 0.5378 |
| post_may | B_pre_long_120 | 16.3693 | -3.5077 | 1.5682 | -0.3538 | 0.5714 | -1.5425 | 0.6465 |
| post_may | C_momentum_60 | 16.4091 | -1.5819 | 1.553 | -0.1589 | 0.7857 | -0.7386 | 0.7578 |
| post_may | D_straddle_TP1.5_SL1.0 | 1.7568 | -1.0 | 0.1751 | -0.1 | 0.7857 | -1.0 | 0.1154 |
| post_may | E_best_straddle | 4.5118 | -1.985 | 0.4472 | -0.1999 | 0.5 | -0.5 | 0.2475 |

## By event type (full-year, unscaled)
| variant | event_group | n | total_return_unscaled_pct | max_drawdown_unscaled_pct | mean | win_rate | mean_excl_largest_winner |
|---|---|---|---|---|---|---|---|
| A_pre_long_60 | CPI | 11 | 9.2568 | -3.9414 | 0.8236 | 0.6364 | 0.5815 |
| A_pre_long_60 | FOMC | 8 | -0.6545 | -3.9135 | -0.0705 | 0.375 | -0.5213 |
| A_pre_long_60 | JACKSON_HOLE | 1 | 7.1518 | 0.0 | 7.1518 | 1.0 | nan |
| A_pre_long_60 | ALL | 20 | 16.3044 | -4.5474 | 0.7823 | 0.55 | 0.4471 |
| A_pre_long_60 | ALL_excl_JH | 19 | 8.5417 | -4.5474 | 0.4471 | 0.5263 | 0.2917 |
| D_straddle_TP1.5_SL1.0 | CPI | 11 | 2.7846 | 0.0 | 0.25 | 1.0 | 0.25 |
| D_straddle_TP1.5_SL1.0 | FOMC | 8 | -0.1256 | -1.0 | -0.0149 | 0.5 | -0.0528 |
| D_straddle_TP1.5_SL1.0 | JACKSON_HOLE | 1 | 0.25 | 0.0 | 0.25 | 1.0 | nan |
| D_straddle_TP1.5_SL1.0 | ALL | 20 | 2.9122 | -1.0 | 0.144 | 0.8 | 0.1385 |
| D_straddle_TP1.5_SL1.0 | ALL_excl_JH | 19 | 2.6555 | -1.0 | 0.1385 | 0.7895 | 0.1323 |

## Variant E (best straddle by full-year) = **straddle_TP3.0_SL0.5** — EXPLORATORY, not final; selected on full-year data so it is in-sample and must not be read as alpha.

## Interpretation (per rules)
- Drawdowns are computed SEPARATELY per split (curves never mixed). Unscaled = 100% gross notional; 10%-account = spec 0.10× factor (straddle 5/5).
- If full-year is ok but pre-May is poor and post-May is good, the strategy likely needs an **ETH price-regime filter** — flagged for a NEXT version; NOT added here.
- `mean_excl_largest_winner` / `_loser` and the ALL_excl_JH row isolate single-event dominance (esp. Jackson Hole). This does NOT prove alpha; n is small (full 20, pre 6, post 14).
- After-fee columns are intentionally excluded from this cost-free run.
- Note: pre_event_long total return partly rides 2025 directional drift; the straddle variants are direction-agnostic and a cleaner volatility read.