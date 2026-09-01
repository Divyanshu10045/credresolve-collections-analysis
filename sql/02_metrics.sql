-- ============================================================
-- METRIC DEFINITIONS — independent of any existing business reporting
-- ============================================================

-- Contact rate = ANSWERED calls / total calls, by month
CREATE OR REPLACE VIEW golden.metric_contact_rate AS
SELECT DATE_TRUNC('month', event_at) AS month,
       100.0 * SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) / COUNT(*) AS contact_rate_pct
FROM golden.calls
GROUP BY 1 ORDER BY 1;

-- RPC = ANSWERED calls excluding WRONG_NUMBER disposition / total calls
CREATE OR REPLACE VIEW golden.metric_rpc AS
SELECT DATE_TRUNC('month', c.event_at) AS month,
       100.0 * SUM(CASE WHEN c.call_status = 'ANSWERED'
                          AND COALESCE(d.disposition_code_clean,'') <> 'WRONG_NUMBER'
                    THEN 1 ELSE 0 END) / COUNT(*) AS rpc_pct
FROM golden.calls c
LEFT JOIN golden.dispositions d ON c.call_id = d.call_id
GROUP BY 1 ORDER BY 1;

-- PTP rate & kept rate
CREATE OR REPLACE VIEW golden.metric_ptp AS
SELECT DATE_TRUNC('month', event_at) AS month,
       COUNT(*) AS ptp_count,
       100.0 * SUM(CASE WHEN status = 'KEPT' THEN 1 ELSE 0 END) / COUNT(*) AS ptp_kept_rate_pct,
       SUM(promised_amount) AS total_promised_amount
FROM raw.promises_to_pay
GROUP BY 1 ORDER BY 1;

-- Recovery rate = SUCCESS payments / total portfolio outstanding (static baseline)
CREATE OR REPLACE VIEW golden.metric_recovery_rate AS
SELECT DATE_TRUNC('month', p.event_at) AS month,
       SUM(p.amount) AS total_recovered,
       SUM(p.amount) / (SELECT SUM(outstanding_amount) FROM golden.accounts) * 100 AS recovery_rate_pct
FROM golden.payments p
WHERE p.payment_status = 'SUCCESS'
GROUP BY 1 ORDER BY 1;

-- Recovery per account touched & per agent-hour
CREATE OR REPLACE VIEW golden.metric_recovery_efficiency AS
WITH monthly_recovery AS (
    SELECT DATE_TRUNC('month', event_at) AS month, SUM(amount) AS recovered
    FROM golden.payments WHERE payment_status='SUCCESS' GROUP BY 1
),
monthly_accounts_touched AS (
    SELECT DATE_TRUNC('month', event_at) AS month, COUNT(DISTINCT account_id) AS accounts_touched
    FROM golden.calls GROUP BY 1
),
monthly_agent_hours AS (
    SELECT DATE_TRUNC('month', login_at) AS month,
           SUM(EXTRACT(EPOCH FROM (logout_at - login_at))/3600) AS agent_hours
    FROM raw.agent_sessions GROUP BY 1
)
SELECT r.month, r.recovered,
       r.recovered / NULLIF(t.accounts_touched,0) AS recovery_per_account,
       r.recovered / NULLIF(h.agent_hours,0) AS recovery_per_agent_hour
FROM monthly_recovery r
JOIN monthly_accounts_touched t ON r.month = t.month
JOIN monthly_agent_hours h ON r.month = h.month
ORDER BY r.month;

-- ============================================================
-- THE HEADLINE CHECK: is the reported 11% MoM improvement real?
-- ============================================================
WITH naive AS (
    SELECT DATE_TRUNC('month', event_at) AS month, SUM(amount) AS recovered
    FROM raw.payments WHERE payment_status='SUCCESS' GROUP BY 1
),
golden AS (
    SELECT DATE_TRUNC('month', event_at) AS month, SUM(amount) AS recovered
    FROM golden.payments WHERE payment_status='SUCCESS' GROUP BY 1
)
SELECT n.month,
       n.recovered AS naive_recovered,
       100.0 * (n.recovered / LAG(n.recovered) OVER (ORDER BY n.month) - 1) AS naive_mom_pct,
       g.recovered AS golden_recovered,
       100.0 * (g.recovered / LAG(g.recovered) OVER (ORDER BY g.month) - 1) AS golden_mom_pct
FROM naive n JOIN golden g ON n.month = g.month
ORDER BY n.month;
