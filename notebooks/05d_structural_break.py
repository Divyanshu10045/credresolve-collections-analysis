"""
PART 5D — STRUCTURAL-BREAK HUNT AT DAILY GRANULARITY
====================================================
Looks for a step change in: (a) new-share of CONTACTED targeting per day,
(b) distinct accounts contacted per day, (c) campaign start density by version.
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

campaigns = pd.read_csv(fr'{DATA}\campaigns.csv', parse_dates=['start_at', 'end_at'])
targeting = pd.read_csv(fr'{DATA}\daily_targeting.csv', parse_dates=['target_date'])

tg = targeting.merge(campaigns[['campaign_id', 'strategy_version']], on='campaign_id', how='left')
tg['new'] = tg.strategy_version.isin(['v2', 'v3'])

print("===== daily new-share of CONTACTED targeting (7-day rolling) =====")
tc = tg[tg.status == 'CONTACTED'].copy()
day = tc.groupby('target_date')['new'].mean().rolling(7).mean() * 100
print(day.round(2).to_string())

print("\n===== campaign start_at by version (monthly) =====")
print(campaigns.assign(m=campaigns.start_at.dt.to_period('M'))
      .pivot_table(index='m', columns='strategy_version', values='campaign_id',
                   aggfunc='count', fill_value=0).to_string())

print("\n===== campaign start dates by version (sorted) =====")
for sv in ['legacy', 'v1', 'v2', 'v3']:
    sub = campaigns[campaigns.strategy_version == sv].start_at.dt.date.sort_values()
    print(sv, "n=", len(sub), "| first", sub.min(), "| last", sub.max())
    print("   ", list(sub))

print("\n===== daily distinct accounts CONTACTED (7d rolling) =====")
cnt = tc.groupby('target_date')['account_id'].nunique().rolling(7).mean()
print(cnt.round(1).to_string())