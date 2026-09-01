"""
PART 5C — ACCOUNT-LEVEL STRATEGY TRAJECTORIES
=============================================
Checks whether accounts SWITCH strategy_version over time (staggered treatment)
versus staying under one version. Builds the raw material for a Did design.
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

tg = targeting.merge(campaigns[['campaign_id', 'strategy_version']], on='campaign_id', how='left')

# CONTACTED = effective delivery. Check switching among CONTACTED-only.
tg_c = tg[tg.status == 'CONTACTED'].copy()
tg_c['new'] = tg_c.strategy_version.isin(['v2', 'v3'])
tg_c['month'] = tg_c.target_date.dt.to_period('M')

# number of distinct versions per account
per_acct = tg_c.groupby('account_id').agg(
    n_versions=('strategy_version', 'nunique'),
    n_rows=('target_date', 'count'),
    n_new=('new', 'sum'),
    n_old=('new', lambda s: (~s).sum()),
    first_d=('target_date', 'min'),
    last_d=('target_date', 'max'),
    ever_new=('new', 'max'),
).reset_index()
print("distinct CONTACTED accounts:", len(per_acct))
print("\naccounts by # distinct strategy_versions (CONTACTED only):")
print(per_acct.n_versions.value_counts().sort_index().to_string())

print("\naccounts by ever_new (touched by v2/v3 at any point):")
print(per_acct.ever_new.value_counts().to_string())

print("\nshare of accounts whose targeting was 100% old vs 100% new vs mixed:")
print((round(per_acct.n_new / per_acct.n_rows).value_counts(normalize=True) * 100).round(1).to_string())

# switch timing: accounts observed under old version first, then new (or vice versa)
def first_last(df):
    df = df.sort_values('target_date')
    return df.strategy_version.iloc[0], df.strategy_version.iloc[-1]

fl = per_acct
sw = tg_c.sort_values('target_date').groupby('account_id')['strategy_version'].agg(list)

def switch_timing(seq):
    if len(seq) < 2:
        return None
    # date at which version category (old/new) flips
    old = seq[0] in ('legacy', 'v1')
    for i, v in enumerate(seq):
        is_old = v in ('legacy', 'v1')
        if is_old != old:
            return i
    return None

# Build per-account monthly dominant strategy to detect a real flip mid-year
pivot = tg_c.pivot_table(index='account_id', columns='month', values='new', aggfunc='mean', fill_value=np.nan)
print("\npivot shape (# accounts x # months of CONTACTED records):", pivot.shape)

# For accounts present both first half and second half, did their new-share increase?
jan_jul = pivot[[p for p in pivot.columns if p in ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07']]]
h1 = ['2026-01', '2026-02', '2026-03']
h2 = ['2026-05', '2026-06', '2026-07']
both = jan_jul.dropna(subset=h1 + h2)
print("\naccounts targeted (CONTACTED) in BOTH H1(Jan-Mar) and H2(May-Jul):", len(both))
print("mean new-share H1 vs H2 for those accounts:")
print(round(both[h1].mean(axis=1).mean() * 100, 1), " vs ", round(both[h2].mean(axis=1).mean() * 100, 1))
shift = both[h2].mean(axis=1) - both[h1].mean(axis=1)
print("distribution of (H2 new-share - H1 new-share):")
print(shift.describe().round(3).to_string())
print("share of such accounts whose new-share rose >0.2 in H2:", (shift > 0.2).mean(),
      "| fell >0.2:", (shift < -0.2).mean())

# Switching around a hypothetical mid-May cutoff
pre = ['2026-01', '2026-02', '2026-03', '2026-04']
post = ['2026-05', '2026-06', '2026-07']
pp = jan_jul.dropna(subset=pre + post)
print("\naccounts CONTACTED in both pre(Jan-Apr) and post(May-Jul):", len(pp))
print("mean new-share pre vs post:", round(pp[pre].mean(axis=1).mean() * 100, 1),
      " vs ", round(pp[post].mean(axis=1).mean() * 100, 1))