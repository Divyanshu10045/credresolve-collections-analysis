import pandas as pd
pd.set_option('display.width', 160)

DATA = '/home/claude/credresolve/data'
GOLD = '/home/claude/credresolve/outputs/golden'

accounts = pd.read_csv(f'{DATA}/accounts.csv')
calls = pd.read_csv(f'{GOLD}/calls_golden.csv')
attempts = pd.read_csv(f'{DATA}/call_attempts.csv')
payments = pd.read_csv(f'{GOLD}/payments_golden.csv')
vendor_t = pd.read_csv(f'{DATA}/vendor_telephony.csv')
campaigns = pd.read_csv(f'{DATA}/campaigns.csv')

acc = accounts[['account_id','risk_segment','dpd','loan_type']].copy()
acc['dpd_bucket'] = pd.cut(acc.dpd, [0,15,30,60,90,9999], labels=['0-15','16-30','31-60','61-90','90+'])

print("="*90); print("DRIVER: RISK SEGMENT — contact rate & recovery"); print("="*90)
c = calls.merge(acc, on='account_id', how='left')
print("Contact rate (ANSWERED %) by risk_segment:")
print(c.groupby('risk_segment', observed=True).apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False).round(2))
p = payments[payments.payment_status=='SUCCESS'].merge(acc, on='account_id', how='left')
print("\nTotal recovered by risk_segment:")
print(p.groupby('risk_segment', observed=True)['amount'].sum().round(0))

print()
print("="*90); print("DRIVER: DPD BUCKET"); print("="*90)
print("Contact rate by dpd_bucket:")
print(c.groupby('dpd_bucket', observed=True).apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False).round(2))
print("\nRecovered amount by dpd_bucket:")
print(p.groupby('dpd_bucket', observed=True)['amount'].sum().round(0))

print()
print("="*90); print("DRIVER: TELEPHONY VENDOR (grouped by real vendor_name, not vendor_id)"); print("="*90)
c2 = calls.merge(vendor_t[['vendor_id','vendor_name']], on='vendor_id', how='left')
print(c2.groupby('vendor_name').apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False).round(2))

print()
print("="*90); print("DRIVER: CAMPAIGN CHANNEL"); print("="*90)
c3 = calls.merge(campaigns[['campaign_id','channel','strategy_version']], on='campaign_id', how='left')
print("Contact rate by campaign channel:")
print(c3.groupby('channel').apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False).round(2))
print("\nContact rate by strategy_version:")
print(c3.groupby('strategy_version').apply(lambda g: (g.call_status=='ANSWERED').mean()*100, include_groups=False).round(2))

print()
print("="*90); print("DRIVER: ATTEMPT FREQUENCY (attempt_no) — does calling more help or hurt?"); print("="*90)
conn_rate = attempts.groupby('attempt_no').apply(lambda g: (g.attempt_status=='CONNECTED').mean()*100, include_groups=False)
print(conn_rate.round(2))
