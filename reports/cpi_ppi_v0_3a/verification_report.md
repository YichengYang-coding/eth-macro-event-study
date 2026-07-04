# v0.3a — Data Verification Report (CPI/PPI 2025)

Canonical timestamp column: **open_time_utc**. Raw rows: 30240; unique event dates: 21; checkpoints: 231 (21 events × 11 offsets).

| check | result |
|---|---|
| 1+3. OHLCV exact match vs raw 1m | PASS (open 231, high 231, low 231, close 231, volume 231 / 231) |
| 2. timestamp == event_time + offset | PASS |
| 4. each event date has 1440 candles | PASS ([np.int64(1440)]) |
| 5. no duplicate timestamps | PASS |
| 6. open_time_utc used as canonical | PASS |
| rows missing a raw match | 0 |

## RESULT: ALL PASS — backtest proceeds