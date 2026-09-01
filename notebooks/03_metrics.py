"""
PART 3 METRICS + PART 2 DRIVER ANALYSIS
=========================================
Builds independent metric definitions and tests each candidate driver.
"""
import pandas as pd
import numpy as np
pd.set_option('display.width', 160)

DATA = '/home/claude/credresolve/data'
GOLD = '/home/claude/credresolve/outputs/golden'

accounts = pd.read_csv(f'{DATA}/accounts.csv', parse_dates=['opened_at'])
calls = pd.read_csv(f'{GOLD}/calls_golden.csv', parse_dates=['event_at'])
attempts = pd.read_csv(f'{DATA}/call_attempts.csv', parse_dates=['event_at'])
disp = pd.read_csv(f'{GOLD}/dispositions_golden.csv', parse_dates=['event_at'])
ptp = pd.read_csv(f'{DATA}/promises_to_pay.csv', parse_dates=['event_at','promised_date'])
payments = pd.read_csv(f'{GOLD}/payments_golden.csv', parse_dates=['event_at'])
sessions = pd.read_csv(f'{DATA}/agent_sessions.csv', parse_dates=['login_at','logout_at'])
vendor_t = pd.read_csv(f'{DATA}/vendor_telephony.csv')
campaigns = pd.read_csv(f'{DATA}/campaigns.csv', parse_dates=['start_at','end_at'])

for df in [calls, attempts, disp, ptp, payments]:
    df['month'] = df['event_at'].dt.to_period('M')

# ============================================================
# METRIC DEFINITIONS (independent of whatever the business currently uses)
# ============================================================
print("="*90)
print("METRIC 1: CONTACT RATE = ANSWERED calls / total calls")
print("="*90)
cr = calls.groupby('month').apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False)
print(cr.round(2))

print()
print("="*90)
print("METRIC 2: RPC (Right-Party Contact) = ANSWERED calls that reached a valid")
print("disposition (excludes WRONG_NUMBER) / total calls")
print("="*90)
calls_disp = calls.merge(disp[['call_id','disposition_code_clean']], on='call_id', how='left')
rpc = calls_disp.groupby('month').apply(
    lambda g: ((g.call_status=='ANSWERED') & (g.disposition_code_clean!='WRONG_NUMBER')).mean()*100,
    include_groups=False)
print(rpc.round(2))

print()
print("="*90)
print("METRIC 3: PTP RATE = PTPs created / RPC count (per month)")
print("METRIC 4: PTP KEPT RATE = PTPs with status=KEPT / total PTPs due that month")
print("="*90)
ptp_count = ptp.groupby('month').size()
ptp_kept = ptp.groupby('month').apply(lambda g: (g.status=='KEPT').mean()*100, include_groups=False)
rpc_count = calls_disp.groupby('month').apply(
    lambda g: ((g.call_status=='ANSWERED') & (g.disposition_code_clean!='WRONG_NUMBER')).sum(),
    include_groups=False)
ptp_rate = (ptp_count / rpc_count * 100)
print(pd.DataFrame({'ptp_count': ptp_count, 'ptp_rate_%_of_RPC': ptp_rate, 'ptp_kept_rate_%': ptp_kept}).round(2))

print()
print("="*90)
print("METRIC 5: RECOVERY RATE = recovered amount / total outstanding under management")
print("(static portfolio outstanding used as denominator baseline)")
print("="*90)
total_outstanding = accounts.outstanding_amount.sum()
rec = payments[payments.payment_status=='SUCCESS'].groupby('month')['amount'].sum()
print((rec / total_outstanding * 100).round(3), "  <- % of total portfolio recovered per month")

print()
print("="*90)
print("METRIC 6: RECOVERY PER ACCOUNT (touched) & PER AGENT-HOUR")
print("="*90)
touched_accounts = calls.groupby('month')['account_id'].nunique()
rec_per_acct = rec / touched_accounts
sessions['hours'] = (sessions.logout_at - sessions.login_at).dt.total_seconds()/3600
sessions['month'] = sessions.login_at.dt.to_period('M')
agent_hours = sessions.groupby('month')['hours'].sum()
rec_per_agent_hour = rec / agent_hours
print(pd.DataFrame({'recovery': rec, 'accounts_touched': touched_accounts,
                     'recovery_per_account': rec_per_acct,
                     'agent_hours': agent_hours,
                     'recovery_per_agent_hour': rec_per_agent_hour}).round(2))
