-- ============================================================
-- GOLDEN DATASET CONSTRUCTION
-- Assumes raw tables loaded as-is into a `raw` schema (Postgres dialect,
-- portable to Snowflake/BigQuery with minor syntax changes)
-- ============================================================

-- ------------------------------------------------------------
-- 1. ACCOUNTS (spine) — passes integrity checks as-is, no cleaning needed
--    beyond flagging unresolved borrower links.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.accounts AS
SELECT
    account_id,
    borrower_id,
    (borrower_id IS NOT NULL) AS borrower_resolved,
    loan_type,
    principal_amount,
    outstanding_amount,
    dpd,
    CASE
        WHEN dpd <= 15 THEN '0-15'
        WHEN dpd <= 30 THEN '16-30'
        WHEN dpd <= 60 THEN '31-60'
        WHEN dpd <= 90 THEN '61-90'
        ELSE '90+'
    END AS dpd_bucket,
    risk_segment,
    status AS current_status,
    opened_at
FROM raw.accounts;

-- ------------------------------------------------------------
-- 2. POINT-IN-TIME ACCOUNT STATUS
--    event_at is canonical; recorded_at is NOT used for ordering
--    (50.3% of rows have recorded_at < event_at — consistent with
--    uniform random jitter, not genuine late-arrival signal).
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.status_history AS
SELECT DISTINCT ON (account_id, event_at, status)
    account_id, event_at, status
FROM raw.account_status_history
ORDER BY account_id, event_at, status;

-- Reconstruct status as of any date: last status change at/before that date,
-- falling back to accounts.csv's current status if no history exists.
CREATE OR REPLACE FUNCTION golden.status_as_of(p_account_id TEXT, p_as_of TIMESTAMP)
RETURNS TEXT AS $$
    SELECT COALESCE(
        (SELECT status FROM golden.status_history
         WHERE account_id = p_account_id AND event_at <= p_as_of
         ORDER BY event_at DESC LIMIT 1),
        (SELECT current_status FROM golden.accounts WHERE account_id = p_account_id)
    );
$$ LANGUAGE SQL STABLE;

-- ------------------------------------------------------------
-- 3. PAYMENTS — deduplicate by payment_reference.
--    Decision: for SUCCESS rows, keep earliest settlement per reference
--    (later SUCCESS rows for the same reference = duplicate gateway
--    callback, not a second real payment). For non-SUCCESS references
--    with no SUCCESS row, keep the most recent status.
--    Impact: reduces naive SUCCESS total by ~14.3%.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.payments AS
WITH ranked_success AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY payment_reference ORDER BY event_at ASC) AS rn
    FROM raw.payments
    WHERE payment_status = 'SUCCESS'
),
refs_with_success AS (
    SELECT DISTINCT payment_reference FROM raw.payments WHERE payment_status = 'SUCCESS'
),
ranked_non_success AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY payment_reference ORDER BY event_at DESC) AS rn
    FROM raw.payments
    WHERE payment_status <> 'SUCCESS'
      AND payment_reference NOT IN (SELECT payment_reference FROM refs_with_success)
)
SELECT payment_id, account_id, event_at, amount, payment_status, payment_method, payment_reference
FROM ranked_success WHERE rn = 1
UNION ALL
SELECT payment_id, account_id, event_at, amount, payment_status, payment_method, payment_reference
FROM ranked_non_success WHERE rn = 1;

-- ------------------------------------------------------------
-- 4. CALLS — dedupe by call_id, keep earliest occurrence.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.calls AS
SELECT DISTINCT ON (call_id)
    call_id, account_id, agent_id, vendor_id, campaign_id,
    event_at, call_status, timezone
FROM raw.calls
ORDER BY call_id, event_at ASC;

-- ------------------------------------------------------------
-- 5. CALL DISPOSITIONS — normalize PROMISE_TO_PAY -> PTP (same
--    outcome, duplicate label; co-occurs across all schema versions,
--    so this is NOT a version-driven rename).
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.dispositions AS
SELECT DISTINCT
    call_id,
    CASE WHEN disposition_code = 'PROMISE_TO_PAY' THEN 'PTP' ELSE disposition_code END
        AS disposition_code_clean,
    event_at,
    disposition_version
FROM raw.call_dispositions;

-- ------------------------------------------------------------
-- 6. VENDOR MAPPING — collapse vendor_id to real vendor_name
--    (multiple vendor_ids map to the same telephony provider).
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW golden.vendor_map AS
SELECT vendor_id, vendor_name FROM raw.vendor_telephony;

-- ------------------------------------------------------------
-- NOTE — borrowers.csv and agents.csv dimension tables are
-- INTENTIONALLY EXCLUDED from golden views beyond their bare ID
-- columns. Their descriptive attributes (name, phone, email, city,
-- state, team, vendor, tenure, status) are statistically decoupled
-- from the ID and cannot support segmentation. See DATA_QUALITY_REPORT.md.
-- ------------------------------------------------------------
