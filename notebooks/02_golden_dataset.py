"""
GOLDEN DATASET PIPELINE — CredResolve Collections Analytics
==============================================================
Documents every cleaning decision inline. Run: python3 02_golden_dataset.py
Outputs golden tables to /home/claude/credresolve/outputs/golden/
"""
import pandas as pd
import numpy as np
import os

DATA = '/home/claude/credresolve/data'
OUT = '/home/claude/credresolve/outputs/golden'
os.makedirs(OUT, exist_ok=True)

log = []
def report(step, raw, kept, note=""):
    rejected = raw - kept
    pct = rejected/raw*100 if raw else 0
    log.append((step, raw, kept, rejected, f"{pct:.2f}%", note))
    print(f"{step:45s} raw={raw:8d}  kept={kept:8d}  rejected={rejected:7d} ({pct:5.2f}%)  {note}")

# ------------------------------------------------------------------
# 1. ACCOUNT SPINE — accounts.csv is the canonical entity table.
#    Verified: account_id has zero duplicates, zero exact-dupe rows.
#    Decision: this is our SOURCE OF TRUTH for account_id, borrower_id (FK),
#    loan_type, principal, outstanding, dpd, risk_segment, opened_at.
# ------------------------------------------------------------------
accounts = pd.read_csv(f'{DATA}/accounts.csv', parse_dates=['opened_at'])
raw_n = len(accounts)
# 455 accounts have null borrower_id — kept, but flagged as unresolved-borrower accounts
# (excluding them would silently shrink the population — a denominator-manipulation risk
# the assignment specifically warns against, so we keep them and flag instead)
accounts['borrower_resolved'] = accounts['borrower_id'].notna()
report("accounts (spine)", raw_n, len(accounts),
       f"{(~accounts.borrower_resolved).sum()} accounts flagged: no borrower_id")

# ------------------------------------------------------------------
# 2. POINT-IN-TIME ACCOUNT STATUS — account_status_history.csv
#    Decision: event_at is the canonical timestamp for status changes.
#    recorded_at is NOT used for ordering — 50.3% of rows have recorded_at
#    BEFORE event_at (impossible for real ingestion), consistent with a
#    uniform random ±24h jitter rather than genuine late-arrival signal.
#    This makes recorded_at unusable for "as of ingestion" logic; event_at
#    is treated as ground truth for when the status change happened.
# ------------------------------------------------------------------
hist = pd.read_csv(f'{DATA}/account_status_history.csv', parse_dates=['event_at','recorded_at'])
raw_n = len(hist)
hist_dedup = hist.drop_duplicates(subset=['account_id','event_at','status'])
report("account_status_history", raw_n, len(hist_dedup), "exact (account,event_at,status) dupes dropped")

def status_as_of(account_ids, as_of_date, hist_df, accounts_df):
    """Reconstruct account status as of a given date using event_at ordering."""
    h = hist_df[hist_df.event_at <= as_of_date].sort_values('event_at')
    latest = h.groupby('account_id').tail(1).set_index('account_id')['status']
    result = latest.reindex(account_ids)
    # accounts with NO history on/before as_of_date fall back to accounts.csv's
    # current status field (documented fallback — see notes)
    fallback = accounts_df.set_index('account_id')['status']
    result = result.fillna(fallback)
    return result

n_no_history = accounts.account_id.nunique() - hist_dedup.account_id.nunique()
print(f"  -> {n_no_history} accounts have ZERO status-history rows; fallback = accounts.csv current status field")

# ------------------------------------------------------------------
# 3. PAYMENTS — the highest-stakes cleaning decision in this pipeline.
#    Two distinct duplication patterns found:
#      (a) Exact full-row duplicates (972 rows / 485 references) — pure
#          re-ingestion noise, e.g. a retry-safe API call inserted twice.
#      (b) Same payment_reference, different payment_id, MULTIPLE SUCCESS
#          rows (2,033 references) — could be legit retry-after-failure,
#          but per-reference multiple SUCCESS rows cannot both be real
#          money (a payment reference is issued once per transaction
#          attempt in every payment gateway design).
#    Decision: for each payment_reference, keep exactly ONE row —
#      - if any SUCCESS rows exist for that reference, keep the
#        EARLIEST SUCCESS (first successful settlement; later "SUCCESS"
#        rows for the same reference are treated as duplicate settlement
#        confirmations, a known payment-gateway callback-retry pattern)
#      - if no SUCCESS rows exist, keep the latest row chronologically
#        (most recent status is most informative for FAILED/PENDING/REVERSED)
#    This is a MATERIAL decision — it changes total recovery by ~14%.
#    Documented explicitly so it can be challenged/changed downstream.
# ------------------------------------------------------------------
payments = pd.read_csv(f'{DATA}/payments.csv', parse_dates=['event_at'])
raw_n = len(payments)

succ = payments[payments.payment_status == 'SUCCESS'].sort_values('event_at')
succ_dedup = succ.drop_duplicates(subset='payment_reference', keep='first')

non_succ = payments[payments.payment_status != 'SUCCESS']
refs_with_success = set(succ.payment_reference)
non_succ_no_success = non_succ[~non_succ.payment_reference.isin(refs_with_success)]
non_succ_dedup = non_succ_no_success.sort_values('event_at').drop_duplicates(subset='payment_reference', keep='last')

payments_golden = pd.concat([succ_dedup, non_succ_dedup], ignore_index=True)
report("payments", raw_n, len(payments_golden),
       f"amount impact: naive SUCCESS sum ={payments[payments.payment_status=='SUCCESS'].amount.sum():,.0f} "
       f"-> golden ={payments_golden[payments_golden.payment_status=='SUCCESS'].amount.sum():,.0f}")

# ------------------------------------------------------------------
# 4. CALLS — drop exact duplicate rows (1,271 found) and duplicate
#    call_id with differing content (1,350 call_ids appear >1x total;
#    keep first occurrence chronologically per call_id).
# ------------------------------------------------------------------
calls = pd.read_csv(f'{DATA}/calls.csv', parse_dates=['event_at'])
raw_n = len(calls)
calls_dedup = calls.sort_values('event_at').drop_duplicates(subset='call_id', keep='first')
report("calls", raw_n, len(calls_dedup), "dedup by call_id, keep earliest event_at")

# ------------------------------------------------------------------
# 5. CALL DISPOSITIONS — normalize legacy synonym codes.
#    PROMISE_TO_PAY and PTP co-occur across ALL disposition_version
#    values at similar rates -> not a version-driven rename, but a
#    genuine duplicate label for the same outcome. Canonicalized to PTP.
# ------------------------------------------------------------------
disp = pd.read_csv(f'{DATA}/call_dispositions.csv', parse_dates=['event_at'])
raw_n = len(disp)
code_map = {'PROMISE_TO_PAY': 'PTP'}
disp['disposition_code_clean'] = disp['disposition_code'].replace(code_map)
disp_dedup = disp.drop_duplicates(subset=['call_id','disposition_code_clean'])
report("call_dispositions", raw_n, len(disp_dedup),
       f"{(disp.disposition_code=='PROMISE_TO_PAY').sum()} PROMISE_TO_PAY rows merged into PTP")

# ------------------------------------------------------------------
# 6. WHATSAPP EVENTS / BORROWERS — drop exact duplicate rows only.
#    Borrower demographic fields (name/phone/email/city/state) are NOT
#    used downstream — see data-quality report: these attributes are
#    statistically decoupled from borrower_id and cannot be trusted for
#    segmentation. borrower_id is retained ONLY as an FK linking accounts.
# ------------------------------------------------------------------
wa = pd.read_csv(f'{DATA}/whatsapp_events.csv')
wa_dedup = wa.drop_duplicates()
report("whatsapp_events", len(wa), len(wa_dedup), "exact dupes dropped")

borrowers_raw = pd.read_csv(f'{DATA}/borrowers.csv')
report("borrowers (dimension — DO NOT TRUST attributes)", len(borrowers_raw),
       borrowers_raw.borrower_id.nunique(),
       "collapsed to distinct borrower_id only; name/phone/email/city/state EXCLUDED from analysis")

# ------------------------------------------------------------------
# SAVE GOLDEN TABLES
# ------------------------------------------------------------------
accounts.to_csv(f'{OUT}/accounts_golden.csv', index=False)
payments_golden.to_csv(f'{OUT}/payments_golden.csv', index=False)
calls_dedup.to_csv(f'{OUT}/calls_golden.csv', index=False)
disp_dedup.to_csv(f'{OUT}/dispositions_golden.csv', index=False)
hist_dedup.to_csv(f'{OUT}/status_history_golden.csv', index=False)

log_df = pd.DataFrame(log, columns=['step','raw_rows','kept_rows','rejected_rows','rejected_pct','note'])
log_df.to_csv(f'{OUT}/cleaning_impact_log.csv', index=False)
print("\nGolden tables written to", OUT)
