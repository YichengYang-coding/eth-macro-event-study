# v0.4 — Step 1 Verification Report

Canonical timestamp: `open_time_utc`. Sources: powell, cpi_ppi, fomc.

## RESULT: ALL PASS — backtest proceeds

- events checked: 20; complete: 20; missing: 0
- duplicate open_time_utc across sources: 0
- all present events have 1440 candles & exact timestamp: yes

| event_name | type | event_time_utc | candles | ts_exists | ok |
|---|---|---|---|---|---|
| CPI_Dec2024 | CPI | 2025-01-15 13:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Jan | FOMC_PRESS_CONFERENCE | 2025-01-29 19:30 | 1440 | True | ✅ |
| CPI_Jan2025 | CPI | 2025-02-12 13:30 | 1440 | True | ✅ |
| CPI_Feb2025 | CPI | 2025-03-12 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Mar | FOMC_PRESS_CONFERENCE | 2025-03-19 18:30 | 1440 | True | ✅ |
| CPI_Mar2025 | CPI | 2025-04-10 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_May | FOMC_PRESS_CONFERENCE | 2025-05-07 18:30 | 1440 | True | ✅ |
| CPI_Apr2025 | CPI | 2025-05-13 12:30 | 1440 | True | ✅ |
| CPI_May2025 | CPI | 2025-06-11 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Jun | FOMC_PRESS_CONFERENCE | 2025-06-18 18:30 | 1440 | True | ✅ |
| CPI_Jun2025 | CPI | 2025-07-15 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Jul | FOMC_PRESS_CONFERENCE | 2025-07-30 18:30 | 1440 | True | ✅ |
| CPI_Jul2025 | CPI | 2025-08-12 12:30 | 1440 | True | ✅ |
| Powell_Jackson_Hole | JACKSON_HOLE | 2025-08-22 14:00 | 1440 | True | ✅ |
| CPI_Aug2025 | CPI | 2025-09-11 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Sep | FOMC_PRESS_CONFERENCE | 2025-09-17 18:30 | 1440 | True | ✅ |
| CPI_Sep2025_Delayed | CPI | 2025-10-24 12:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Oct | FOMC_PRESS_CONFERENCE | 2025-10-29 18:30 | 1440 | True | ✅ |
| FOMC_Press_Conference_Dec | FOMC_PRESS_CONFERENCE | 2025-12-10 19:30 | 1440 | True | ✅ |
| CPI_Nov2025_Delayed | CPI | 2025-12-18 13:30 | 1440 | True | ✅ |