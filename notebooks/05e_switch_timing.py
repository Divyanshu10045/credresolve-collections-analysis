"""
PART 5E — VERSION-SWITCH TIMING + MONTHLY RECOVERY REFERENCE
============================================================
(a) timing distribution of per-account version switches (CONTACTED)
(b) reference monthly recovery tables (golden, deduped) to counterfactualize
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
GOLD = os.path.join(HERE, '..', 'golden_dataset')

campaigns = pd.read_csv(fr'{DATA}\campaigns.csv', parse_dates=['start_at', 'end_at'])
targeting = pd.read_csv(fr'{DATA}\daily_targeting.csv', parse_dates=['target_date'])
payments = pd.read_csv(fr'{GOLD}\payments_golden.csv', parse_dates=['event_at'])
calls = pd.read_csv(fr'{GOLD}\calls_golden.csv', parse_dates=['event_at'])
accounts = pd.read_csv(fr'{GOLD}\accounts_golden.csv')

tg = targeting.merge(campaigns[['campaign_id', 'strategy_version']], on='campaign_id', how='left')
tc = tg[tg.status == 'CONTACTED'].sort_values('target_date').copy()
tc['d'] = tc.target_date.dt.date

def switches(g):
    g = g.sort_values('target_date')
    vers = g.strategy_version.tolist()
    dates = g.target_date.tolist()
    out = []
    for i in range(1, len(vers)):
        if vers[i] != vers[i - 1]:
            out.append((vers[i - 1], vers[i], dates[i].date()))
    return out

sw = tc.groupby('account_id').apply(lambda g: switches(g), include_groups=False)
sw = sw.dropna()
print("accounts with >=1 version switch (CONTACTED):", len(sw))
flat = [(acc, f, t, d) for acc, lst in sw.items() if lst for (f, t, d) in lst]
sdf = pd.DataFrame(flat, columns=['account_id', 'from_v', 'to_v', 'switch_date'])
print("total switches:", len(sdf))
print("switch matrix from->to:\n", sdf.pivot_table(index='from_v', columns='to_v', values='account_id', aggfunc='count', fill_value=0).to_string())

sdf['switch_date'] = pd.to_datetime(sdf['switch_date'])
print("\nswitches by month of switch_date:")
print(sdf.switch_date.dt.to_period('M').value_counts().sort_index().to_string())

print("\nswitch types by month:")
sdf['type'] = sdf.from_v + '->' + sdf.to_v
print(pd.crosstab(sdf.switch_date.dt.to_period('M'), sdf.type).to_string())

print("\n=================== MONTHLY REFERENCE ===================")
p = payments[payments.payment_status == 'SUCCESS']
p['month'] = p.event_at.dt.to_period('M')
m = p.groupby('month')['amount'].sum()
print("monthly SUCCESS recovery (golden):")
print((m / 1e6).round(2).rename('recovery_M').to_string())
print("\nMoM % change:", (100 * (m.pct_change())).round(2).to_string())
print("\nJan-Jul total:", round(m.loc['2026-01':'2026-07'].sum() / 1e6, 1), "M")
print("Aug total:", round(m['2026-08'] / 1e6, 1), "M")

cc = calls.copy(); cc['month'] = cc.event_at.dt.to_period('M')
print("\naccounts with calls by month:")
print(cc.groupby('month')['account_id'].nunique().to_string())
print("\naccounts with SUCCESS payment by month:")
print(p.groupby('month')['account_id'].nunique().to_string())
print("\nSUCCESS payments count by month:")
print(p.groupby('month')['payment_id'].count().to_string())