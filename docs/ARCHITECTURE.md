# Production Architecture: Collections Analytics Pipeline

## Pipeline Overview

![Pipeline architecture](images/architecture_diagram.svg)

Data flows left to right: 17 source tables land in `raw.*`, get typed and validated in `staging.*`,
cleaned per the decisions in `DATA_QUALITY_REPORT.md`, then split into `feature.*` (derived
signals) and `metrics.*` (rate-normalized aggregates) before reaching the dashboard.

## Data Contracts
- Each source system owns a **contract**: expected columns, types, nullable fields, and a `source_extracted_at` watermark. A contract violation (new/missing column, type drift) fails the staging load loudly rather than silently coercing.
- `account_id` is the only field trusted as a hard join key across all fact tables. `agent_id`/`borrower_id` are trusted as FKs but NOT as attribute-lookup keys (see Data Quality Report §1.1) — this constraint is enforced in the contract, not just documented.

## Primary Keys
- `accounts.account_id`, `payments.payment_reference` (not `payment_id` — reference is the true dedup key), `calls.call_id`, `promises_to_pay` has no natural key; use `(account_id, event_at)` composite with a generated surrogate.

## Metric Definitions (single source of truth)
All metric SQL lives in `sql/02_metrics.sql` as versioned views — not recomputed ad hoc in the BI tool. Any metric redefinition is a PR against that file, reviewed like code, so "the business definition" can't silently drift between the dashboard and someone's spreadsheet.

## Data Lineage
Every `golden.*` view carries a comment block naming: (1) which `raw.*` tables it reads, (2) which cleaning decision from `DATA_QUALITY_REPORT.md` it implements, (3) what row-count impact that decision has (from `cleaning_impact_log`). Lineage is queryable, not just documented — `information_schema` + view-dependency graph gives an auto-generated lineage diagram.

## Incremental Processing & Late-Arriving Data
- Fact tables (`calls`, `payments`, `dispositions`, etc.) load incrementally by `event_at` watermark, **not** `recorded_at` — we established `recorded_at` is unreliable (50% show negative lag).
- A **7-day reopen window**: any batch touches the last 7 days of already-loaded partitions to absorb late arrivals, then re-runs downstream `golden.*` and `metrics.*` views for that window only.
- Payments specifically: reference-level dedup logic must re-run on every incremental load, since a duplicate SUCCESS row can arrive in a later batch than its original.

## Backfills
- Golden/metric views are **views over staging**, not materialized copies, specifically so a cleaning-logic change (e.g., a different payment-dedup rule) doesn't require a manual backfill — it's live on next query. Where materialization is needed for performance, materialized views are refreshed by full-table rebuild (data volume here doesn't justify incremental materialization complexity).

## Data Quality Checks (automated, not just manual review)
- **Referential integrity**: % of `accounts.borrower_id` missing from `borrowers.id` (currently 898) — alert if this jumps outside historical range.
- **Duplicate rate**: % of `payments.payment_reference` with >1 SUCCESS row — alert if it deviates from the ~14% baseline (a sudden spike suggests a new gateway-retry bug; a sudden drop to 0% suggests upstream dedup was silently added, which would need a metric-definition review).
- **Attribute stability check**: for `agents`/`borrowers`, % of IDs with >1 distinct value for a "should be stable" column (name, team) — this should be near 0% in a healthy system; currently it's ~100%, which is the trigger that would have caught this issue in production before an analyst had to find it by hand.
- **Timestamp sanity**: % of rows where `recorded_at < event_at` — alert if the rate isn't ~50% (uniform noise) or moves toward a systematic bias.

## Monitoring & Anomaly Detection
- Each `metrics.*` view is snapshotted daily; a simple z-score/IQR check on day-over-day and month-over-month deltas flags anomalies for analyst review — **crucially, this same check would have caught the "11% MoM" claim automatically**, since a >2-sigma single-month move is exactly the kind of thing that shouldn't be reported as a stable trend without a trend-level (not point-level) statistical test behind it.
- Dashboard displays a confidence band (e.g., trailing 3-month volatility) alongside every headline number, so "one big month" can't be presented as "sustained improvement" again.
