"""
PART 5 — EXPLORE STRATEGY CHANGE-POINT
======================================
Locates when the targeting strategy changed by looking at:
  - campaigns.csv: start_at/end_at + strategy_version (legacy, v1, v2, v3)
  - daily_targeting.csv: account-level targeting records over time
Prints diagnostics only; no golden files written here.
"""
import pandas as pd
import numpy as np
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

campaigns = pd.read_csv(fr'{DATA}\campaigns.csv', parse_dates=['start_at', 'end_at'])
targeting = pd.read_csv(fr'{DATA}\daily_targeting.csv', parse_dates=['target_date'])

print("campaigns rows:", len(campaigns))
print("strategy_version counts:", campaigns.strategy_version.value_counts().to_dict())
print("\ncampaign channel distribution:\n", campaigns.channel.value_counts().to_string())
print("\ntarget_definition distribution:\n", campaigns.target_definition.value_counts().to_string())
print("\ncampaign start_at range:", campaigns.start_at.min(), "->", campaigns.start_at.max())
print("campaign end_at range:", campaigns.end_at.min(), "->", campaigns.end_at.max())

print("\n=================== strategy_version over time (campaigns active-days) ===================")
# active-days per day by strategy_version
day = pd.date_range('2026-01-01', '2026-08-15')
active = pd.DataFrame(index=day)
for sv in ['legacy', 'v1', 'v2', 'v3']:
    sub = campaigns[campaigns.strategy_version == sv]
    cnt = []
    for d in day:
        cnt.append(((sub.start_at <= d) & (sub.end_at >= d)).sum())
    active[sv] = cnt
active['total'] = active.sum(axis=1)
print(active.resample('W').sum().to_string())

print("\n=================== daily_targeting overview ===================")
print("targeting rows:", len(targeting))
print("status values:", targeting.status.value_counts(dropna=False).to_dict())
print("priority values:", targeting.priority.value_counts(dropna=False).to_dict())
print("recommended_channel:\n", targeting.recommended_channel.value_counts(dropna=False).to_string())
print("target_date range:", targeting.target_date.min(), "->", targeting.target_date.max())
print("distinct accounts targeted:", targeting.account_id.nunique())
print("distinct campaigns used:", targeting.campaign_id.nunique())

tg = targeting.merge(campaigns[['campaign_id', 'strategy_version', 'channel', 'target_definition']],
                     on='campaign_id', how='left')
print("\ntargeting rows missing campaign link:", tg.strategy_version.isna().sum())

print("\n=================== targeting volume by strategy_version over time ===================")
tg['week'] = tg.target_date.dt.to_period('W')
pivot = tg.pivot_table(index='week', columns='strategy_version', values='account_id', aggfunc='count', fill_value=0)
pivot['total'] = pivot.sum(axis=1)
pivot['new_share_%'] = 100 * (pivot.get('v2', 0) + pivot.get('v3', 0)) / pivot['total']
print(pivot.to_string())

print("\n=================== does targeting volume follow campaigns active-days? ===================")
tg.shape
agg = tg.groupby(['target_date', 'strategy_version']).size().unstack(fill_value=0)
print(agg.resample('W').sum().to_string())