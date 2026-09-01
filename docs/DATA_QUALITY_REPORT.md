# Data Quality Report

## 1. Major Data Issues Found

### 1.1 Dimension tables (`agents.csv`, `borrowers.csv`) — descriptive attributes decoupled from ID
**Severity: Critical.** A single `agent_id` (avg. 30 rows) shows a *different* name, team, vendor, status, and join date on nearly every row — only 10 distinct names exist across 30,000 rows, reused randomly. `borrowers.csv` shows the same pattern (10 names total; phone/email/created_at all vary per `borrower_id`). This is worse than the "same agent under multiple identifiers" risk the assignment named — it's the reverse: **one identifier, many unrelated identities.**
- **Detection:** grouped by ID, measured `nunique()` of every descriptive column; found near-total instability.
- **Treatment:** excluded these tables' descriptive columns entirely from the golden dataset. IDs retained only as foreign keys for joining fact tables to each other, not for attribute lookup.
- **Business impact:** any historical report segmenting by agent team, agent tenure, borrower city, or borrower language is built on a broken join and should not be trusted.

### 1.2 Duplicate payments — material and mechanically distinct from ordinary noise
- 972 exact full-row duplicates (485 references).
- 2,033 `payment_reference`s have **multiple independent `SUCCESS` rows** — not retries-after-failure, but duplicate settlement confirmations.
- **Impact quantified:** naively summing `SUCCESS` amounts overstates recovery by **14.28%**, consistently across months (13.7%–15.0%).
- **Treatment:** dedupe by `payment_reference`, keeping the earliest `SUCCESS` row per reference.

### 1.3 Timestamp/timezone unreliability — system-wide
- `calls.timezone` is uncorrelated with the actual hour encoded in `event_at` (correlation 0.13–0.21 across the three stated zones); hour-of-day distribution is **flat across all 24 hours** for every stated timezone.
- Same flat pattern independently confirmed in `agent_sessions.login_at`.
- `account_status_history.recorded_at` is earlier than `event_at` in 50.3% of rows — consistent with random ±24h jitter, not genuine late-arrival.
- **Treatment:** `event_at` used as the sole canonical timestamp throughout; `recorded_at` and `timezone` excluded from any time-of-day or ingestion-order logic. **Any "optimal calling time" conclusion from this dataset would be manufactured, not discovered** — flagged explicitly rather than forced.

### 1.4 Disposition code duplication
Minor but worth flagging: `PROMISE_TO_PAY` and `PTP` show up as two separate codes at similar rates across every `disposition_version`, so it's not a version rename, just a duplicate label. Merged them to `PTP` in the golden dataset.

### 1.5 PTP status vs. actual payment reality — severe disconnect
- Of accounts with a PTP marked `KEPT`, only **41.2%** have *any* successful payment ever recorded, at any date, on any account. Even with an unbounded matching window, 58.5% show zero matching payment.
- **Business impact:** `promises_to_pay.status` cannot be used as a proxy for real repayment behavior. The commonly-tracked "PTP kept rate" is not validated against cash.

### 1.6 Referential gaps
455 accounts have null `borrower_id`, and another 898 referenced `borrower_id`s do not exist in `borrowers.csv`. I retained these records and flagged them via `borrower_resolved` rather than dropping them, since doing so would itself create a denominator-manipulation risk.

### 1.7 Vendor ID fragmentation
- Multiple `vendor_id`s map to the same real `vendor_name` (e.g., 4 distinct IDs all "Airtel").
- **Treatment:** vendor-level analysis grouped by `vendor_name`, not `vendor_id`.

### 1.8 Weak cross-table attribution
- Only ~15% of successful payments have any call/WhatsApp/SMS/field-visit touchpoint within 5 days beforehand; 85% show **no attributable touchpoint at all**, even across all four channels combined.
- **Business impact:** channel ROI comparisons in this dataset are necessarily low-confidence — most recovery cannot be causally tied to any specific outreach action with the data available.

### 1.9 Reported data window narrower than stated
- The assignment states ~12 months of data; actual event-level activity (calls, payments, PTPs, field visits) spans **Jan 1 – Aug 8/12, 2026 (~7.3 months)**, with August visibly truncated (payments drop from ~₹180–190M/month to ~₹48M).
- **Treatment:** August excluded from all month-on-month trend calculations.

## 2. What Held Up (not everything is broken)
- `accounts.csv`: zero duplicate keys, stable `risk_segment`/`dpd`/`outstanding_amount` — used as the analytical spine.
- `agent_id` and `account_id` as **join keys** (not attribute sources) are consistent across fact tables — 1,000 distinct agent IDs appear consistently in `calls`, `agent_sessions`, and `agents.csv`.
- Payment amounts, dates, and account linkage inside `payments.csv` itself are internally consistent once deduplicated.

## 3. Raw → Rejected/Corrected → Golden (row-level impact)
| Table | Raw rows | Golden rows | Rejected | % | Note |
|---|---|---|---|---|---|
| accounts | 30,000 | 30,000 | 0 | 0% | 455 flagged `borrower_resolved=false`, none dropped |
| account_status_history | 60,000 | see log | — | — | exact (account, event_at, status) dupes dropped |
| payments | 25,986 | see log | — | ~14.3% $ impact | dedup by `payment_reference` |
| calls | 91,350 | see log | — | — | dedup by `call_id`, keep earliest |
| call_dispositions | see log | see log | — | — | `PROMISE_TO_PAY`→`PTP` merge + dupe drop |
| whatsapp_events | see log | see log | — | — | exact dupes dropped |

*(Exact counts: see `golden_dataset/cleaning_impact_log.csv`, generated by the pipeline.)*

## 4. Key Assumptions Carried Forward
- `event_at` is treated as ground truth for all timing; `recorded_at`/`timezone` are not trusted for ordering or localization.
- Borrower/agent demographic segmentation is **not attempted** anywhere in this analysis — any such finding elsewhere should be treated with suspicion.
- Payment-reference-level dedup keeps the *earliest* SUCCESS row; this is a documented, challengeable choice, not the only valid one.
