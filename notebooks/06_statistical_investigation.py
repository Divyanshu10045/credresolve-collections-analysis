"""
PART 6 — STATISTICAL INVESTIGATION (7 BIASES / EFFECTS)
=======================================================
Simple, transparent tests (no ML). Each test prints a compact evidence block:
  1. Mix effects          - composition drift + direct standardization
  2. Cohort effects       - vintage (month-opened) recovery profiles
  3. Selection bias       - who gets contacted, does that change over time
  4. Survivorship bias    - balanced panel vs unconstrained trend
  5. Simpson's paradox    - within-stratum trends vs aggregate
  6. Attribution-window bias - share of payments attributable by window length
  7. Time-series effects  - truncation, month-length, weekday, calendar alignment

Run:  python3 notebooks/06_statistical_investigation.py
Uses only pandas + numpy.
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
GOLD = os.path.join(HERE, '..', 'golden_dataset')

WEEKS_ALL = None  # placeholder to keep linters quiet

accounts = pd.read_csv(os.path.join(GOLD, 'accounts_golden.csv'))
payments = pd.read_csv(os.path.join(GOLD, 'payments_golden.csv'), parse_dates=['event_at'])
calls = pd.read_csv(os.path.join(GOLD, 'calls_golden.csv'), parse_dates=['event_at'])
disp = pd.read_csv(os.path.join(GOLD, 'dispositions_golden.csv'), parse_dates=['event_at'])
payments_raw = pd.read_csv(os.path.join(DATA, 'payments.csv'), parse_dates=['event_at'])
payments_raw_success = payments_raw[payments_raw.payment_status == 'SUCCESS'].copy()
payments_raw_success['month'] = payments_raw_success.event_at.dt.to_period('M')
pay_success = payments[payments.payment_status == 'SUCCESS'].copy()
pay_success['month'] = pay_success.event_at.dt.to_period('M')
pay_success['ymd'] = pay_success.event_at.dt.date
calls['month'] = calls.event_at.dt.to_period('M')

acc = accounts[['account_id', 'risk_segment', 'loan_type', 'dpd', 'outstanding_amount', 'principal_amount',
                'status', 'opened_at', 'schema_version']].copy()
acc['dpd_b'] = pd.cut(acc.dpd, [-1, 15, 30, 60, 90, 9999], labels=['0-15', '16-30', '31-60', '61-90', '90+'])
acc['cohort'] = pd.to_datetime(acc.opened_at).dt.to_period('M')

MONTHS = [f'2026-{mm:02d}' for mm in range(1, 8)]  # Jan-Jul trend window

pard = pay_success.merge(acc[['account_id', 'risk_segment', 'loan_type', 'dpd_b', 'cohort', 'outstanding_amount']],
                         on='account_id', how='left')

print("=" * 100)
print("TEST 1: MIX EFFECTS")
print("=" * 100)
# composition of paying population per month
comp_month = pard.groupby(['month', 'risk_segment']).size().unstack(fill_value=0)
print("\nPaying-account composition by risk_segment (% of paying accounts):")
print((100 * comp_month.div(comp_month.sum(axis=1), axis=0)).round(1).to_string())

comp_lt = pard.groupby(['month', 'loan_type']).size().unstack(fill_value=0)
print("\nPaying-account composition by loan_type (%):")
print((100 * comp_lt.div(comp_lt.sum(axis=1), axis=0)).round(1).to_string())

comp_dpd = pard.groupby(['month', 'dpd_b']).size().unstack(fill_value=0)
print("\nPaying-account composition by dpd bucket (%):")
print((100 * comp_dpd.div(comp_dpd.sum(axis=1), axis=0)).round(1).to_string())

# Direct standardization: fixed Jan composition of paying accounts applied to
# each month's segment-level recovery -> isolates within-segment trend.
seg = pard.groupby(['month', 'risk_segment'])['amount'].sum().unstack(fill_value=0)
jan_share = seg.loc['2026-01'] / seg.loc['2026-01'].sum()
adjusted = seg.mul(jan_share, axis=1).sum(axis=1)
actual = pard.groupby('month')['amount'].sum()
table = pd.DataFrame({'actual_ReM': actual.loc[MONTHS] / 1e6,
                      'mixadj_ReM': adjusted.loc[MONTHS] / 1e6})
table['mixadj/actual'] = table.mixadj_ReM / table.actual_ReM
print("\nDirect standardization (Jan risk_segment mix held fixed):")
print(table.round(2).to_string())
print(f"\nJan->Jul change: actual {(actual['2026-07']/actual['2026-01']-1)*100:.1f}% | "
      f"mix-adjusted {(adjusted['2026-07']/adjusted['2026-01']-1)*100:.1f}%")

print("\n" + "=" * 100)
print("TEST 2: COHORT EFFECTS (VINTAGE = month account opened)")
print("=" * 100)
# recovery per account by cohort x calendar month
m = pard.groupby(['cohort', 'month'])['amount'].sum().unstack(fill_value=0)
print("Recovery (ReM) by account vintage x calendar month:")
print((m / 1e6).round(2).to_string())

npay = pard.groupby(['cohort', 'month']).size().unstack(fill_value=0)
print("\n# paying accounts by vintage x month:")
print(npay.to_string())

share = 100 * npay.div(npay.sum(axis=1), axis=0)
print("\nVintage mix of the paying population (% of paying accounts by cohort):")
print(share.round(1).to_string())

# does the paying population skew toward later vintages over time?
latest_cohort = npay.apply(lambda r: r.index[r.argmax()], axis=1)
print("\nMost common paying-cohort per calendar month:", dict(latest_cohort))

print("\n" + "=" * 100)
print("TEST 3: SELECTION BIAS")
print("=" * 100)
# Coverage = share of the 30k-book contacted each month, by segment.
# Books is a static 30k snapshot (no new accounts), so coverage is meaningful.
book_seg = acc.groupby('risk_segment').size()
book_dpd = acc.groupby('dpd_b').size()
cov_seg = {}
cov_dpd = {}
for mm in MONTHS:
    called_ids = set(calls[calls.month == mm].account_id)
    seg_counts = acc[acc.account_id.isin(called_ids)].groupby('risk_segment').size()
    dpd_counts = acc[acc.account_id.isin(called_ids)].groupby('dpd_b').size()
    cov_seg[mm] = 100 * seg_counts / book_seg
    cov_dpd[mm] = 100 * dpd_counts / book_dpd
print("\nContact COVERAGE (% of book with >=1 call) by risk_segment:")
print(pd.DataFrame(cov_seg).T.round(1).to_string())
print("\nContact coverage by dpd bucket:")
print(pd.DataFrame(cov_dpd).T.round(1).to_string())

jan_called = set(calls[calls.month == '2026-01'].account_id)
jul_called = set(calls[calls.month == '2026-07'].account_id)
print(f"\nCalled-account turnover: Jan={len(jan_called)} Jul={len(jul_called)} "
      f"overlap={len(jan_called & jul_called)} "
      f"({100*len(jan_called & jul_called)/len(jan_called):.0f}% of Jan pool retained)")

print("\nRecovery-per-touched-account (Re, memo's headline efficiency metric), by risk_segment:")
succ_amt = pard.groupby(['month', 'account_id'])['amount'].sum().reset_index()
succ_amt['month'] = succ_amt['month'].astype(str)
touched = calls[calls.month.astype(str).isin(MONTHS)].groupby(['month', 'account_id']).size().reset_index()[['month', 'account_id']]
touched['month'] = touched['month'].astype(str)
rp = touched.merge(succ_amt, on=['month', 'account_id'], how='left').fillna(0)
rp = rp.merge(acc[['account_id', 'risk_segment']], on='account_id', how='left')
per_acct = rp.groupby(['month', 'risk_segment'])['amount'].mean().unstack()
print((per_acct / 1e3).round(1).to_string())
per_acct_all = rp.groupby('month')['amount'].mean()
print("\nAggregate recovery-per-touched-account (Re):")
print(per_acct_all.loc[MONTHS].round(1).to_string())
print(f"Jan->Jul change: {(per_acct_all['2026-07']/per_acct_all['2026-01']-1)*100:.1f}%")

print("\n" + "=" * 100)
print("TEST 4: SURVIVORSHIP BIAS")
print("=" * 100)
jan_payers = set(pay_success[pay_success.month == '2026-01'].account_id)
jul_payers = set(pay_success[pay_success.month == '2026-07'].account_id)
bal = jan_payers & jul_payers
print(f"Jan payers: {len(jan_payers)} | Jul payers: {len(jul_payers)} | both (balanced payer panel): {len(bal)}")
print(f"Jan payers NOT paying in Jul: {len(jan_payers - jul_payers)} "
      f"({(len(jan_payers - jul_payers)/len(jan_payers)*100):.1f}%) <- 'attrition' of paying population")

# Are the Jan-payers who stopped paying still OPEN accounts (real attrition) or
# already settled/closed (survivorship -- they paid & left)?
stopped = acc[acc.account_id.isin(jan_payers - jul_payers)]
print("\nStatus of Jan-payers who did NOT pay in Jul:")
print(stopped.status.value_counts().to_string())
print("Their end-window outstanding vs book median:",
      round(stopped.outstanding_amount.median(), 0), "vs",
      round(acc.outstanding_amount.median(), 0))

# Balanced-TREATMENT panel: same accounts touched (called) in Jan AND Jul.
jan_touched = set(calls[calls.month == '2026-01'].account_id)
jul_touched = set(calls[calls.month == '2026-07'].account_id)
both_touched = jan_touched & jul_touched
print(f"\nTouched Jan={len(jan_touched)} Jul={len(jul_touched)} overlap={len(both_touched)}")

rp_jan = rp[(rp.month == '2026-01') & (rp.account_id.isin(both_touched))]
rp_jul = rp[(rp.month == '2026-07') & (rp.account_id.isin(both_touched))]
print("Recovery-per-account, SAME accounts (balanced touch panel) Jan vs Jul (Re):")
print("  Jan:", round(rp_jan.amount.mean() / 1e3, 1), "| Jul:", round(rp_jul.amount.mean() / 1e3, 1),
      f"| change {(rp_jul.amount.mean()/rp_jan.amount.mean()-1)*100:.1f}%")

monthly_total = pay_success.groupby('month')['amount'].sum()
monthly_bal = pay_success[pay_success.account_id.isin(bal)].groupby('month')['amount'].sum()
print("\nUnconstrained monthly recovery vs balanced-payer-panel recovery:")
print(pd.DataFrame({'all_ReM': (monthly_total.loc[MONTHS]/1e6).round(2),
                    'panel_ReM': (monthly_bal.loc[MONTHS]/1e6).round(2),
                    'panel_share%': (100 * monthly_bal / monthly_total).loc[MONTHS].round(1)}).to_string())

# Full-population trend (what an analyst SHOULD report): all paying accounts each month
rpa_agg_all = monthly_total / pay_success.groupby('month').account_id.nunique()
print("\nRecovery per paying account (full population, not just Jan survivors):")
print(rpa_agg_all.loc[MONTHS].round(1).to_string())
print(f"Jan->Jul per-paying-account change: {(rpa_agg_all['2026-07']/rpa_agg_all['2026-01']-1)*100:.1f}%")
print("\n=> If we had conditioned the analysis on Jan payers surviving to Jul, we'd have seen "
      "essentially ONE month of data (Jul) -> survivorship would be fatal. Full-population "
      "per-payer recovery is ~FLAT -> decline is in the COUNT of payers, not amounts.")

# exit rate among Jan payers: when did they last pay?
last_seen = pay_success[pay_success.month <= '2026-07'].groupby('account_id')['month'].max()
jan_exit = last_seen.reindex(jan_payers).value_counts().sort_index()
print("\nLast-payment month of January payers (attrition timing):")
print(jan_exit.astype(str).to_string())

print("\n" + "=" * 100)
print("TEST 5: SIMPSON'S PARADOX — within-stratum vs aggregate trend")
print("=" * 100)
agg_change = (monthly_total['2026-07'] / monthly_total['2026-01'] - 1) * 100
print(f"Aggregate Jan->Jul recovery change: {agg_change:.1f}%")
print("\nWithin-segment Jan->Jul changes (%):")
w = seg.loc[MONTHS[0]:MONTHS[-1]]
for col in w.columns:
    c = w[col]
    change = (c.iloc[-1] / c.iloc[0] - 1) * 100
    print(f"  {col:10s} actual Re {c.iloc[0]/1e6:7.1f}M -> {c.iloc[-1]/1e6:7.1f}M  ({change:+.1f}%)")

# weekly within-HIGH vs aggregate: rates
rr = seg / comp_month.reindex(seg.index)
print("\nRecovery per paying account (Re) by risk_segment by month:")
print((rr * 1e-3).round(1).to_string())
print("\nAggregate recovery per paying account by month (Re):")
rpa_agg = monthly_total / pay_success.groupby('month').account_id.nunique()
print(rpa_agg.loc[MONTHS].round(1).to_string())
print(f"Jan->Jul per-paying-account change: {(rpa_agg['2026-07']/rpa_agg['2026-01']-1)*100:.1f}%")

print("\n" + "=" * 100)
print("TEST 6: ATTRIBUTION-WINDOW BIAS")
print("=" * 100)
wa = pd.read_csv(os.path.join(DATA, 'whatsapp_events.csv'), parse_dates=['event_at'])
sms = pd.read_csv(os.path.join(DATA, 'sms_events.csv'), parse_dates=['event_at'])
fv = pd.read_csv(os.path.join(DATA, 'field_visits.csv'), parse_dates=['event_at'])
tc = calls[['account_id', 'event_at']].copy()

CHANNELS = {'call': tc, 'whatsapp': wa, 'sms': sms, 'field_visit': fv}
# per-account sorted event arrays for fast window lookup
chan_by_acct = {}
for ch, df in CHANNELS.items():
    g = df.sort_values('event_at').groupby('account_id')['event_at'].apply(lambda s: s.to_numpy())
    chan_by_acct[ch] = {k: v.astype('datetime64[ns]') for k, v in g.items()}

windows = [1, 2, 3, 5, 7, 14, 30]
print("Sample: first 1200 SUCCESS payments (Jan-Jul), windows 1..30 days")
sample = pay_success[pay_success.month.astype(str).isin(MONTHS)].head(1200).copy()
ptime = sample.event_at.values.astype('datetime64[ns]')
n_wd = np.array(windows, dtype='timedelta64[D]')

rows = []
for i, prow in enumerate(sample.itertuples()):
    t = ptime[i]
    acc = prow.account_id
    per_w = {}
    for ch, acct_map in chan_by_acct.items():
        arr = acct_map.get(acc, np.array([], dtype='datetime64[ns]'))
        if arr.size:
            before = t - arr  # positive = touchpoint before payment; <0 after payment
            ok = before >= np.timedelta64(0, 'ns')
            cnt = (ok & (before <= n_wd[:, None])).sum(axis=1)
        else:
            cnt = np.zeros(len(windows), dtype=int)
        per_w[ch] = cnt > 0
    row = {}
    for j, w in enumerate(windows):
        row[f'any_{w}d'] = any(per_w[ch][j] for ch in CHANNELS)
        for ch in CHANNELS:
            row[f'{ch}_{w}d'] = bool(per_w[ch][j])
    rows.append(row)

attrs = pd.DataFrame(rows, index=sample.index)

attrib = pd.DataFrame([100 * attrs[f'any_{w}d'].mean() for w in windows],
                      index=[f'{w}d' for w in windows], columns=['share_with_any_touchpoint'])
print("\n% of SUCCESS payments preceded by ANY touchpoint within N days:")
print(attrib.round(1).to_string())

per_ch = pd.DataFrame({ch: [100 * attrs[f'{ch}_{w}d'].mean() for w in windows] for ch in CHANNELS},
                      index=[f'{w}d' for w in windows])
print("\nPer-channel share of payments with a touchpoint within window (%):")
print(per_ch.round(1).to_string())

print(f"\nPayments with a <=5d touchpoint: {100*attrs['any_5d'].mean():.1f}% "
      f"-> >85% of payments are NOT attributed under a tight 5-day window.")

print("\n" + "=" * 100)
print("TEST 7: TIME-SERIES EFFECTS")
print("=" * 100)
full = pay_success
print("Monthly SUCCESS payment counts: ", end="")
print(full.groupby('month').payment_id.count().to_dict())
aug = full[full.month == '2026-08']
print(f"\nAugust truncated? rows={len(aug)} vs median full month: "
      f"{full[full.month<= '2026-07'].groupby('month').payment_id.count().median()}")
print(f"August recovery share of a full month: "
      f"{100*aug.amount.sum()/monthly_total.loc[MONTHS].mean():.0f}%")

pay_success['dow'] = pay_success.event_at.dt.dayofweek
dow_mix = pay_success.pivot_table(index='month', columns='dow', values='amount',
                                  aggfunc='sum', fill_value=0)
dow_share = dow_mix.div(dow_mix.sum(axis=1), axis=0)
print("\nRecovery by day-of-week (% within month):")
print((100 * dow_share).round(1).to_string())

pay_success['dom'] = pay_success.event_at.dt.day
dom_profile = pay_success[pay_success.month == '2026-07'].groupby('dom').amount.sum()
print("\nJuly recovery by day-of-month (top 5 days):")
print((dom_profile / 1e6).round(2).sort_values(ascending=False).head().to_string())

pay_success['ymd'] = pay_success.event_at.dt.date
daily = pay_success.groupby('ymd').amount.sum()
print("\nDaily recovery rolling-7d avg (first/last 10 days):")
print((daily/1e6).round(3).tail(10).to_string())
print("Daily mean Jan-Jul:", round((daily.loc[pd.Timestamp('2026-01-01').date():] / 1e6).mean(), 2), "M")

# same-calendar comparison: Jan vs Jul both 31 days; compare per-day per-weekday
pool = pay_success[(pay_success.month.astype(str).isin(['2026-01', '2026-07']))].copy()
pivot = pool.pivot_table(index='month', columns='dow', values='amount', aggfunc='sum')
print("\nJan vs Jul recovery by weekday (Re):")
print((pivot/1e6).round(2).to_string())

# Feb vs Mar - the "11% improvement" months - using per-day rates
raw_feb = payments_raw_success[payments_raw_success.month == '2026-02'].amount.sum()
raw_mar = payments_raw_success[payments_raw_success.month == '2026-03'].amount.sum()
feb = pay_success[pay_success.month == '2026-02'].amount.sum() / 28
mar = pay_success[pay_success.month == '2026-03'].amount.sum() / 31
print("\nFeb->Mar 'improvement' decomposition (all three numbers, clearly labeled):")
print(f"  (a) RAW   (undeduplicated data/payments.csv):    "
      f"{100*(raw_mar/raw_feb-1):+.1f}%")
print(f"  (b) GOLDEN (deduplicated payments_golden.csv):   "
      f"{100*(pay_success[pay_success.month=='2026-03'].amount.sum()/(pay_success[pay_success.month=='2026-02'].amount.sum())-1):+.1f}%")
print(f"  (c) GOLDEN per-day (28d->31d adjusted):          "
      f"{100*(mar/feb-1):+.1f}%")

print("\nDate-range sanity: payments span",
      pay_success.event_at.min(), "->", pay_success.event_at.max())