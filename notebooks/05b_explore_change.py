"""
PART 5B — WHAT ACTUALLY CHANGED MID-YEAR?
=========================================
Probes for the "targeting strategy change" across several candidate dimensions:
  recommended_channel mix, target_definition mix, status mix, priority mix,
  risk/dpd composition of targeted pool, and call channel usage.
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
GOLD = os.path.join(HERE, '..', 'golden_dataset')

campaigns = pd.read_csv(fr'{DATA}\campaigns.csv', parse_dates=['start_at', 'end_at'])
targeting = pd.read_csv(fr'{DATA}\daily_targeting.csv', parse_dates=['target_date'])
accounts = pd.read_csv(fr'{GOLD}\accounts_golden.csv')
calls = pd.read_csv(fr'{GOLD}\calls_golden.csv', parse_dates=['event_at'])
payments = pd.read_csv(fr'{GOLD}\payments_golden.csv', parse_dates=['event_at'])

tg = targeting.merge(campaigns[['campaign_id', 'strategy_version', 'channel', 'target_definition']],
                     on='campaign_id', how='left')
tg = tg.merge(accounts[['account_id', 'risk_segment', 'dpd', 'loan_type']], on='account_id', how='left')

wk = tg['target_date'].dt.isocalendar().week.astype(int)
tg['period'] = np.where(tg['target_date'].dt.month <= 3, 'Q1',
               np.where(tg['target_date'].dt.month <= 5, 'AprMay', 'rest'))

print("=================== 1. recommended_channel mix by MONTH ===================")
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='recommended_channel',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 2. target_definition mix by MONTH ===================")
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='target_definition',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 3. targeting status mix by MONTH ===================")
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='status',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 4. risk_segment of TARGETED pool by MONTH ===================")
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='risk_segment',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 5. dpd bucket of TARGETED pool by MONTH ===================")
tg['dpd_b'] = pd.cut(tg.dpd, [-1, 15, 30, 60, 90, 9999], labels=['0-15', '16-30', '31-60', '61-90', '90+'])
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='dpd_b',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 6. strategy_version mix among TARGETED by MONTH ===================")
print(tg.pivot_table(index=tg.target_date.dt.to_period('M'), columns='strategy_version',
                     values='account_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 7. CALL volume & channel by MONTH ===================")
c = calls.merge(campaigns[['campaign_id', 'strategy_version', 'channel']], on='campaign_id', how='left')
print(c.pivot_table(index=c.event_at.dt.to_period('M'), columns='call_status',
                    values='call_id', aggfunc='count', fill_value=0).to_string())
print("\nanswered rate by month:",
      (c.groupby(c.event_at.dt.to_period('M')).apply(
          lambda g: (g.call_status == 'ANSWERED').mean(), include_groups=False) * 100).round(2).to_string())

print("\ncall-linked strategy_version mix by MONTH (%):")
print(c.pivot_table(index=c.event_at.dt.to_period('M'), columns='strategy_version',
                    values='call_id', aggfunc='count', fill_value=0).apply(lambda r: 100*r/r.sum(), axis=1).round(1).to_string())

print("\n=================== 8. monthly recovery by strategy_version (targeting-linked) ===================")
tg_succ = tg[tg.status == 'CONTACTED']
pm = payments[payments.payment_status == 'SUCCESS']
tgm = tg.reset_index().merge(pm, on='account_id', how='inner')
tgm['pay_month'] = tgm.event_at.dt.to_period('M')
tgm['tg_month'] = tgm.target_date.dt.to_period('M')
print(tgm.pivot_table(index='tg_month', columns='strategy_version',
                      values='amount', aggfunc='sum', fill_value=0).round(0).to_string())

print("\n=================== 9. monthly recovery by target_definition (targeting-linked) ===================")
print(tgm.pivot_table(index='tg_month', columns='target_definition',
                      values='amount', aggfunc='sum', fill_value=0).round(0).to_string())