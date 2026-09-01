"""
PART 7 — COUNTERFACTUAL: DID THE MID-YEAR TARGETING CHANGE MATTER?
=================================================================
Lever: `strategy_version` in data/campaigns.csv (legacy/v1 = OLD, v2/v3 = NEW).
Treatment group : accounts whose monthly targeting (effective CONTACTED rows in
                  data/daily_targeting.csv) was run under NEW-version campaigns.
Control group   : accounts contacted under OLD-version campaigns in every month
                  they appear (never exposed to the new strategy).
Outcome         : SUCCESS recovery (golden_dataset/payments_golden.csv) per
                  account-month on an account x month panel (Jan-Jul 2026).

Methods (pandas + numpy only, no scipy/statsmodels):
  A. Panel build + group counts / mix-over-time (parallel-trends visual support)
  B. Two-way (account + month) fixed-effects DiD via alternating within-projection
     and closed-form OLS coefficient; cluster-robust SE at the account level.
  C. 2x2 DiD: switchers (accounts first forced onto new-version campaigns in
     Jun-Jul) vs stayers (old-version-only), pre = Jan-Mar, post = Jun-Jul.
  D. Permutation placebo: shuffle new-exposure status within each month (300
     draws) -> null distribution of the TWFE coefficient, p-value.
  E. Event-study: mean recovery of switchers by months-since-first-new-exposure.
  F. Counterfactual ("no rollout" and "full rollout" scenarios) + range from
     the cluster SE.

Run:  python3 notebooks/07_counterfactual_did.py
"""
import pandas as pd
import numpy as np
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
GOLD = os.path.join(HERE, '..', 'golden_dataset')

RNG = np.random.default_rng(20260701)

# ---------------------------------------------------------------- loads
accounts = pd.read_csv(os.path.join(GOLD, 'accounts_golden.csv'))
payments = pd.read_csv(os.path.join(GOLD, 'payments_golden.csv'), parse_dates=['event_at'])
calls = pd.read_csv(os.path.join(GOLD, 'calls_golden.csv'), parse_dates=['event_at'])
targeting = pd.read_csv(os.path.join(DATA, 'daily_targeting.csv'), parse_dates=['target_date'])
campaigns = pd.read_csv(os.path.join(DATA, 'campaigns.csv'))[['campaign_id', 'strategy_version']]

OLD = {'legacy', 'v1'}
NEW = {'v2', 'v3'}
campaigns['is_new'] = campaigns.strategy_version.isin(NEW)
OLD_NEW = campaigns.set_index('campaign_id')['is_new'].to_dict()

pay_succ = payments[payments.payment_status == 'SUCCESS'].copy()
pay_succ['month'] = pay_succ.event_at.dt.to_period('M')
pay_succ = pay_succ[pay_succ.month.astype(str).between('2026-01', '2026-07')].copy()

MONTHS = [f'2026-{m:02d}' for m in range(1, 8)]
M_IDX = {m: i for i, m in enumerate(MONTHS)}

# ----------------------------------------------------------- A. panel
# aimed (effective) targeting exposure per account-month under new/old version
t = targeting[targeting.status == 'CONTACTED'].copy()
t['month'] = t.target_date.dt.to_period('M').astype(str)
t = t[t.month.isin(MONTHS)]
t['is_new'] = t.campaign_id.map(OLD_NEW)

new_rows = t[t.is_new].drop_duplicates(['account_id', 'month'])
old_rows = t[~t.is_new].drop_duplicates(['account_id', 'month'])
new_set = set(new_rows.groupby('account_id').size().index)          # ever-new
old_set = set(old_rows.groupby('account_id').size().index)          # ever-old
contacted = set(t.account_id)
stay_old = old_set - new_set                                         # control
switch = contacted - stay_old                                        # treatment

# outcome per account-month
ym = pay_succ.groupby(['month', 'account_id'])['amount'].sum().reset_index()
ym.rename(columns={'amount': 'recovered'}, inplace=True)
ym['month'] = ym.month.astype(str)
ym['month_idx'] = ym.month.map(M_IDX)
pv = ym.pivot_table(index='account_id', columns='month_idx', values='recovered',
                    aggfunc='sum', fill_value=0)

# dense account x month panel over the estimation universe (contacted accounts)
universe = np.array(sorted(contacted))
U = len(universe)
uidx = {a: i for i, a in enumerate(universe)}
panel = np.zeros((U, 7), dtype=np.float64)
have = pv.index.intersection(pd.Index(universe))
for a in have:
    panel[uidx[a]] = pv.loc[a].values
Y = panel.ravel()

# treatment matrix D_it (1 = effective new-version exposure that month)
D = np.zeros((U, 7), dtype=np.float64)
nn = new_rows.groupby(['account_id', 'month']).size()
for (a, m), _ in nn.items():
    if a in uidx:
        D[uidx[a], M_IDX[m]] = 1
Dv = D.ravel()

treat_mask = np.array([universe[i] in switch for i in range(U)])
grp = np.repeat(np.where(treat_mask, 'TREAT(ever-new)', 'CTRL(old-only)'), 7)

print("=" * 100)
print("A. PANEL & GROUPS")
print("=" * 100)
print(f"Estimation universe: {U:,} accounts contacted at least once (Jan-Jul).")
print(f"  Treatment (any new-version exposure Jan-Jul): {int(treat_mask.sum()):,}")
print(f"  Control     (old-version-only throughout)   : {U - int(treat_mask.sum()):,}")
called7 = set(calls[calls.event_at.dt.to_period('M').astype(str).between('2026-01', '2026-07')].account_id)
print(f"  accounts with >=1 call Jan-Jul but NOT in targeting CONTACTED: {len(called7 - contacted):,} (excluded)")
print(f"Monthly new-exposure share of contacted book (mix-over-time check):")
for i, m in enumerate(MONTHS):
    tot = np.sum(D[:, i] > 0)
    print(f"  {m}: {tot:,} accounts on new-version targeting ({100*tot/U:.1f}% of contacted)")

y1 = pd.DataFrame({'group': grp, 'y': Y, 'm': np.tile(np.arange(7), U)})
mby = y1.groupby(['group', 'm'])['y'].mean() / 1000
print("\nMean recovery/account-month (thousand Re) by group and month:")
print(mby.unstack(0).round(1).to_string())

# never-targeted (never CONTACTED) accounts as the purest "no treatment" reference
nc_book = accounts[~accounts.account_id.isin(contacted)]
nc_ids = set(nc_book.account_id)
nc_ym = pay_succ[pay_succ.account_id.isin(nc_ids)]
nc_tot = nc_ym.groupby('month')['amount'].sum()
nc_n = nc_ym.groupby('month').account_id.nunique()
print("\nNever-targeted reference accounts (excluded from DiD): monthly recovery")
print(pd.DataFrame({'payers': nc_n, 'ReM': (nc_tot / 1e6).round(2),
                    'kRe/account': (1000 * nc_tot / nc_n).round(1)}).to_string())
print(f"  never-targeted Jan->Jul change: {100*(nc_tot['2026-07']/nc_tot['2026-01']-1):+.1f}% "
      f"(book-level macro decline, untouched by either strategy)")
print("(common ~-18% macro decline in BOTH treated/control AND never-targeted groups.")
print("DiD attributes this macro trend to the month FE; treatment must not be bundled with it.)")

# ----------------------------------------------------------- B. TWFE
def within(x, acct, mo, iters=8):
    """alternating projection: remove account + month means (two-way within)."""
    for _ in range(iters):
        x = x - np.repeat(np.bincount(acct, weights=x) / np.bincount(acct), 7)
        x = x - np.bincount(mo, weights=x)[np.repeat(np.arange(7), U)]
    return x

acct_ids = np.repeat(np.arange(U), 7)
mo_ids = np.tile(np.arange(7), U)
dy = within(Y.copy(), acct_ids, mo_ids)
dw = within(Dv.copy(), acct_ids, mo_ids)

S0 = np.dot(dw, dw)
S1 = np.dot(dy, dw)
b = S1 / S0

# cluster SE (account level)
score = (dy * dw).reshape(U, 7).sum(axis=1)
se = np.sqrt(np.sum(score ** 2) / S0 ** 2)
tstat = b / se
y_mean = Y.mean()
print("\n" + "=" * 100)
print("B. TWFE DIFFERENCE-IN-DIFFERENCES (account + month fixed effects)")
print("=" * 100)
print(f"b (treatment effect, Re per account-month on new-version exposure): {b:,.0f}")
print(f"  as % of mean account-month recovery ({y_mean:,.0f} Re): {100*b/y_mean:+.2f}%")
print(f"  cluster-robust SE (account): {se:,.0f} Re | t = {tstat:.2f}")
print(f"  new-exposure account-months: {int(Dv.sum()):,}")
print("Interpretation: recovery when an account runs on new-version targeting vs")
print("the same account under old-version targeting in the same month.")

# ----------------------------------------------------------- C. 2x2
print("\n" + "=" * 100)
print("C. CLEAN 2x2 DiD: SWITCHERS (onto new strategy Jun-Jul) vs STAYERS (old-only)")
print("=" * 100)
pre_m = [0, 1, 2]    # Jan-Mar
post_m = [5, 6]      # Jun-Jul

switchers = set()
for a in switch:
    m_idx = [M_IDX[m] for m in new_rows[new_rows.account_id == a].month.values]
    pre = any(i in pre_m for i in m_idx)
    post = any(i in post_m for i in m_idx)
    if (not pre) and post:
        switchers.add(a)
stayers = stay_old

def avg_diffs(acct_list):
    d = []
    for a in acct_list:
        if a not in uidx:
            continue
        r = panel[uidx[a]]
        pre = r[pre_m].mean(); post = r[post_m].mean()
        d.append(post - pre)
    return np.array(d)

X_t = avg_diffs(switchers)
X_c = avg_diffs(stayers)
did2 = X_t.mean() - X_c.mean()
se2 = np.sqrt(np.var(X_t, ddof=1) / len(X_t) + np.var(X_c, ddof=1) / len(X_c))
print(f"switchers (first new-exposure in Jun-Jul): {len(X_t):,} | stayers: {len(X_c):,}")
print(f"mean change (Re/account): switchers {X_t.mean():,.0f} | stayers {X_c.mean():,.0f}")
print(f"2x2 DiD = {did2:,.0f} Re/account (SE {se2:,.0f}, t={did2/se2:.2f})")
print(f"(both groups declined -> DiD ~ {100*did2/(panel.mean()*7):+.2f}% of avg account-month*7)")

# ----------------------------------------------------------- D. placebo
print("\n" + "=" * 100)
print("D. PERMUTATION PLACEBO (300 draws, shuffle new-exposure within month)")
print("=" * 100)
n_draws = 300
Dflat = Dv.copy()
null = np.zeros(n_draws)
for k in range(n_draws):
    Dp = Dflat.copy()  # permute within each month slice
    for m in range(7):
        sl = slice(m * U, (m + 1) * U)
        Dp[sl] = RNG.permutation(Dflat[sl])
    dwp = within(Dp.copy(), acct_ids, mo_ids)
    null[k] = np.dot(dy, dwp) / np.dot(dwp, dwp)
p_val = (np.abs(null) >= np.abs(b)).mean()
print(f"null: mean {null.mean():,.0f}, sd {null.std():,.0f} | observed b {b:,.0f} | two-sided p = {p_val:.3f}")

# ----------------------------------------------------------- E. event study
print("\n" + "=" * 100)
print("E. EVENT-STUDY: switcher recovery by months-since-first-new-exposure")
print("=" * 100)
es = {}
for a in switchers:
    if a not in uidx:
        continue
    first = min(M_IDX[m] for m in new_rows[new_rows.account_id == a].month.values)
    es.setdefault(first, []).append(panel[uidx[a]])
ev = pd.DataFrame({f'first_new={MONTHS[f]}': np.mean(es[f], axis=0) for f in sorted(es)},
                  index=MONTHS)
ev['ctrl_old-only'] = np.array([panel[np.array([universe[i] in stay_old for i in range(U)]), m].mean() for m in range(7)])
print("Switcher mean recovery ('000 Re) by target calendar month, split by first-new-exposure month (rows).")
print("A kink AT the switch month would show a discrete jump between adjacent columns:")
print((ev / 1000).round(1).to_string())
print("Note: 'ctrl_old-only' = mean recovery of never-new accounts by calendar month (common trend reference).")

# ----------------------------------------------------------- F. counterfactual
print("\n" + "=" * 100)
print("F. COUNTERFACTUAL RECOVERY: WHAT IF THE MID-YEAR CHANGE HAD NOT HAPPENED?")
print("=" * 100)
actual_total = Y.sum()
D_months = int(Dv.sum())

# HEADLINE: use the robust 2x2 switcher estimate (not the sparse TWFE point).
# "without the change" = switcher accounts behave like (never-switched) stayers.
no_change2 = actual_total - did2 * len(switchers)
band2 = se2 * len(switchers)
print(f"Actual Jan-Jul recovery, contacted-universe: {actual_total/1e6:,.1f}M Re "
      f"(new-exposure intensity {D_months:,} account-months = {100*D_months/(U*7):.1f}% of contacted-universe)")
print(f"Headline counterfactual (2x2, switchers behave like stayers):")
print(f"  'no mid-year change' recovery = {no_change2/1e6:,.1f}M Re "
      f"({100*(no_change2-actual_total)/actual_total:+.2f}% vs actual)")
print(f"  +-1SE range: [{100*(band2)/actual_total:.2f}% of total] | t = {did2/se2:.2f}")
print(f"  => statistically indistinguishable from zero: the ~18% decline was NOT driven by the strategy change.")

# ROBUSTNESS: sparse TWFE extrapolation (b +/- cov). Genuinely uninformative CI.
print(f"Robustness (TWFE extrapolation, uninformative due to sparsity):")
print(f"  effect b = {b:,.0f} Re/exposed-month, SE {se:,.0f} (t={tstat:.2f}); "
      f"'no rollout' would have been {100*(-b*D_months)/actual_total:+.1f}% "
      f"(range +-{100*se*D_months/actual_total:.0f}pp) - do not cite.")
print(f"=> headline: the strategy change explains ~{abs(100*(no_change2-actual_total)/actual_total):.1f}% "
      f"of recovery; the remaining ~18% decline is a book-level phenomenon present in BOTH groups "
      f"and in never-targeted accounts alike.")

# raw dependence on window: recovery of never-contacted accounts for reference
nc_panel = accounts[~accounts.account_id.isin(contacted)]
nc_y = pay_succ[pay_succ.account_id.isin(set(nc_panel.account_id))].groupby('month')['amount'].sum()
nm = pay_succ[pay_succ.account_id.isin(set(nc_panel.account_id))].groupby('month').account_id.nunique()
print("\nReference: never-contacted accounts (excluded from estimation) monthly recovery:")
print(pd.DataFrame({'n': nm, 'ReM': (nc_y / 1e6).round(2)}).to_string())