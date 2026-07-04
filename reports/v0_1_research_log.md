# v0.1 Research Log — FOMC 事件定义修正（FOMC_STATEMENT）

日期：2025（v0.1）
范围：仅修正事件定义并重建 price / OI+price case 表。**未改动策略核心逻辑、未调参、未使用未来数据、未因结果改阈值。**

---

## 1. 为什么修正事件时间

旧的结果桶（`fomc_2025_event_*`）实际上把 **下午 2:30pm ET 的新闻发布会（press conference）开始时间**当成了利率决议/点火时刻。这是错的：

- FOMC 的**利率决议与声明（statement）是在 2:00pm ET 发布**，这一分钟才是离散信息冲击、才是仓位开始 unwind 的点火点。
- 2:30pm 的发布会是**另一个、且性质不同的信息事件**（主席问答、前瞻指引语气），它发生在声明之后 30 分钟，不能代表"决议公布"这一离散事件。

把事件锚点放在 2:30pm，会导致 pre/post 窗口整体错位 30 分钟：pre 窗口里其实已经包含了声明发布后的剧烈行情，post 窗口又错过了真正的点火 candle。因此本次把 8 个事件的锚点统一改回 **2:00pm ET = statement release**。

DST 处理已核对：3–10 月为 EDT(UTC−4)，2:00pm ET = **18:00 UTC**；1 月与 12 月为 EST(UTC−5)，2:00pm ET = **19:00 UTC**。manifest 中 `event_utc` 已正确反映这一点（2025-01-29 与 2025-12-10 为 19:00，其余为 18:00）。

## 2. press conference 与 statement 的区别

| | FOMC statement / 利率决议 | press conference（发布会） |
|---|---|---|
| 时间 | 2:00pm ET（= 本次 `event_utc`） | 2:30pm ET（旧桶误用的时间） |
| 内容 | 离散的利率决定 + 政策声明文本 | 主席讲话 + 记者问答 |
| 市场含义 | 决议公布瞬间，crowded 多空仓位开始 unwind | 语气/前瞻指引的二次定价，连续、叙事驱动 |
| 是否本策略目标 | **是**（点火区间） | 否（不同事件，单独建桶） |

旧桶并未作废，而是**备份重命名为 `*_pressconf_*`** 保留，便于将来单独研究发布会窗口。

## 3. 本次固定事件 universe（8 个，事先固定）

| event_id | event_utc (statement) | entry_utc (T−10) | decision_utc (T−5) | utc_date_file |
|---|---|---|---|---|
| fomc_statement_2025_01 | 2025-01-29 19:00 | 18:50 | 18:55 | 2025-01-29 |
| fomc_statement_2025_02 | 2025-03-19 18:00 | 17:50 | 17:55 | 2025-03-19 |
| fomc_statement_2025_03 | 2025-05-07 18:00 | 17:50 | 17:55 | 2025-05-07 |
| fomc_statement_2025_04 | 2025-06-18 18:00 | 17:50 | 17:55 | 2025-06-18 |
| fomc_statement_2025_05 | 2025-07-30 18:00 | 17:50 | 17:55 | 2025-07-30 |
| fomc_statement_2025_06 | 2025-09-17 18:00 | 17:50 | 17:55 | 2025-09-17 |
| fomc_statement_2025_07 | 2025-10-29 18:00 | 17:50 | 17:55 | 2025-10-29 |
| fomc_statement_2025_08 | 2025-12-10 19:00 | 18:50 | 18:55 | 2025-12-10 |

定义：
- `event_utc` = 声明发布分钟（点火 candle）。
- `entry_utc` = T−10。
- `decision_utc` = T−5。
- `pre_15m_high/low` 使用窗口 **[event_utc − 15min, event_utc)**，左闭右开，**不含 event candle**。
- post 窗口 **从 event_utc 开始**（点火 candle 计入）。primary post = 10 分钟（对齐 spec 的最大持仓 10min），另记 30/60min 仅作描述性观察。
- 所有时间主逻辑只用 **UTC**；不使用北京时间作为筛选时间。

## 4. 这不是 cherry-pick，而是事件定义修正

- 事件集合是**事先固定的 2025 全部 8 次 FOMC 会议**，没有按结果挑事件、没有剔除任何一次。
- 修正只动了**时间戳定义**（2:30pm→2:00pm，并定义 entry=T−10、decision=T−5），对 8 个事件**统一施加**，与各自盈亏无关。
- **没有改任何阈值**（±1.5% 突破、±2.2% 延续、0.7% 移动止损、+3%/+6% 止盈、10min 最大持仓全部保持原值）。
- price case 表只做**测量**（pre/post 极值、收益、是否突破 pre 区间），不含任何为结果调过的参数。
- 未使用未来数据：pre/entry/decision 特征严格止于 `event_utc` 之前；post 窗口仅为描述性结果，不回灌到入场决策。

## 5. 当前限制

- **OI 是 Binance 代理（proxy），不是全交易所合并 OI。** OI+price 表中 `oi_source = binance_proxy`。Binance 量大、有代表性，但不能等同全市场持仓；跨所 OI、资金费率、强平数据留待后续版本。
- 本次只重建了 **price case / OI+price case**；**策略回测（strategy.py/backtest.py）未在本次重跑范围内**，也未改动。
- ⚠️ **待协调项**：新 manifest 把 `entry_utc` 定义为 T−10，而策略规格/`StrategyConfig` 当前入场为 T−5（即现在的 `decision_utc`）。本次刻意未改策略核心逻辑，故二者尚未对齐。下次重跑策略回测时需明确：入场到底用 T−10 还是 T−5。这里先记录，不擅自更改。
- v0.1 仍未建模真实盘口深度、mark-price 强平机制、资金费率、交易所保证金规则、tick 级撮合（与 spec §18 一致）。

## 6. 本次产出文件

- 新 manifest：`data/eth_fomc_2025_1m_okx/event_manifest_2025_fomc_statement_times.csv`
- 旧桶备份重命名：
  - `reports/fomc_2025_event_price_cases.csv` → `reports/fomc_2025_pressconf_price_cases.csv`
  - `reports/fomc_2025_event_oi_price_cases.csv` → `reports/fomc_2025_pressconf_oi_price_cases.csv`
  - `data/.../event_manifest_2025_fomc_entry_times.csv` → `data/.../event_manifest_2025_fomc_pressconf_times.csv`
- 新结果：
  - `reports/fomc_2025_statement_price_cases.csv`
  - `reports/fomc_2025_statement_oi_price_cases.csv`
- 完整性检查：`tests/test_event_data_integrity.py`（已指向 statement manifest，新增 entry/decision/event 偏移与 event_type 校验）。

## 7. 复现实验命令（在项目根目录、真实数据就位后）

```bash
# 备份重命名旧 press-conf 桶（可先 --dry-run 预演）
python scripts/migrate_pressconf.py --dry-run
python scripts/migrate_pressconf.py

# 数据完整性测试
python -m pytest -q

# 重建 statement price / OI+price 案例
python run_statement_pipeline.py --oi-dir data/eth_fomc_2025_oi_binance
```
