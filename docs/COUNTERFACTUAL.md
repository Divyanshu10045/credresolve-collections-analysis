# Counterfactual: What Would Recovery Have Been Without the Mid-Year Targeting Change?

**Script:** `notebooks/07_counterfactual_did.py`
**Lever studied:** `strategy_version` in `data/campaigns.csv` — the mid-year rollout moved targeting from the **old generation** (`legacy`, `v1`) to the **new generation** (`v2`, `v3`)
**Treatment timing definition:** effective targeting exposure = account has a `status == "CONTACTED"` row in `data/daily_targeting.csv` whose campaign maps to a `strategy_version` **(effective delivery of the campaign to the account on that day)**
**Outcome:** deduplicated SUCCESS recovery (₹) per account-month, `golden_dataset/payments_golden.csv`, Jan–Jul 2026

> All numbers are in ₹. "Recovery" always means the deduplicated (golden) SUCCESS amount. August is excluded (truncated month — see `STATISTICAL_INVESTIGATION.md` Test 7).

---

## The question

The mid-year change moved a share of collections targeting onto `v2`/`v3` campaigns. Recovery still fell 18.6% over Jan–Jul. **Would recovery have been materially different if the change had *not* happened** — i.e., is the change responsible for anything?

## Treatment group

**Accounts whose targeting was ever delivered under a new-version campaign (v2/v3)** during Jan–Jul 2026 (measured at account-month level; an account-month is "exposed" if it has ≥1 CONTACTED target row under a new-version campaign that month).

- 4,889 accounts ever exposed to new-version targeting.
- The **switchers** sub-population used for the clean DiD: **1,372 accounts** whose *first* new-version exposure arrived in Jun–Jul 2026 with no new-version exposure in Jan–Mar.

## Control group

**Old-version-only accounts** — accounts contacted under `legacy`/`v1` campaigns only, in every month they appear (4,212 accounts). **Not** never-contacted accounts: the counterfactual question is "new strategy vs. the strategy it replaced," so the appropriate comparison is old-strategy accounts, not no-outreach accounts. (Never-contacted accounts are still examined separately as a *macro* reference — see below.)

## Identification strategy

Difference-in-differences on an **account × month panel** (9,101 contacted accounts × 7 months):

1. **Two-way fixed effects (TWFE).** `Recovery_it = α_i + γ_t + β·Exposed_it + ε_it` estimated by account- and month-demeaning (alternating within-projection) with cluster-robust (account) standard errors. The month FE absorbs the book-wide ~18% decline so it cannot be mis-attributed to the strategy; the account FE absorbs time-invariant account differences.
2. **Clean 2×2 DiD.** Pre = Jan–Mar, Post = Jun–Jul. Treatment = switchers (first new-version exposure Jun–Jul); control = old-version-only accounts. Estimator: (Post−Pre)treated − (Post−Pre)control. This is the headline estimate because it avoids TWFE's reliance on low-frequency exposure variation.
3. **Permutation placebo.** Shuffle exposed-status within each month (300 draws) to build a null distribution for β under "treatment is meaningless."
4. **Event study.** Switcher recovery by calendar month, split by first-new-exposure month, looking for a discrete kink at the switch month.

## Assumptions (and how we checked them)

| Assumption | Check | Result |
|---|---|---|
| **Parallel trends** — switchers would have followed controls | Pre-period (Jan–Mar) mean recovery: controls ₹6.0k/5.4k/6.1k per account-month; treatment ₹5.8k/5.0k/6.0k; event study shows switchers tracking the control trend **before and after** their switch, with no kink at the switch month | Supported (levels similar, no pre-divergence) |
| **No anticipation** — no response before exposure | Switchers defined by *first-ever* new exposure; a random-shuffle placebo shows the observed β is indistinguishable from noise (p = 0.62) and a timing-placebo is flat | Supported |
| **SUTVA / no spillovers** | Borrowers could have multiple accounts; spillovers (a collection contact cascading across an account's sibling accounts) are unobservable | Cannot test — acknowledged limitation |
| **Month FE represent macro shock** | Book-wide decline is common to treated, control, **and never-targeted accounts** (never-targeted: 126.99 → 103.06 ₹M, **−18.8%**) — i.e., the "shock" is a book-level phenomenon hitting everyone equally, so the month FE is the right absorber | Supported |
| **TWFE appropriate** | Only ~8% of contacted account-months are exposed; sparse → the TWFE point estimate is imprecise (flagged below); the robust 2×2 is used as headline | Handled via design choice |

## Confounders considered

- **Which accounts get routed to the new strategy** (selection). Mixed into account FE; and exposure share is flat at ~8% of the contacted book *every* month (7.5–8.8% Jan–Jul) — there is no structural break in the *share* of accounts ever on the new strategy (details in `notebooks/05d_structural_break.py`). Observable account quality (risk, DPD) is balanced across the book (Test 3 of the statistical investigation).
- **Macro borrower environment during the window** — absorbed by month FE; confirmed common across all groups.
- **Lumpy, sparse payments** — the outcome is mostly zeros with occasional large payouts, which makes per-account-month estimates noisy (this is why the placebo and 2×2 carry the weight).

## Estimate (headline)

**2×2 DiD (switchers vs. old-only stayers):**

- Switchers' mean recovery change (Post−Pre): **−₹451/account**
- Stayers' mean recovery change (Post−Pre): **−₹796/account**
- **ΔΔ = +₹345/account (SE ₹652, t = 0.53)** → effect is statistically indistinguishable from zero (about +0.1% of annualized per-account recovery).

**Robustness (TWFE):** β = +₹32,366 per exposed account-month, SE ₹43,856 (t = 0.74); permutation placebo p = 0.62. The sparsity of exposure makes this estimate imprecise; it is not cited as a point estimate.

**Event study:** switchers show *no discrete kink* at their switch month — their recovery tracks the control group's calendar pattern through the switch (e.g., accounts first exposed in June: pre-switch Apr/May ≈ ₹7.6k/6.5k, switch month Jun = ₹4.2k, post Jul = ₹4.8k, vs. control Jun = ₹4.5k, Jul = ₹5.6k).

## Counterfactual result

**"What if the mid-year change had not happened?"** Using the robust 2×2 estimate and assuming switcher account-months behave like stayers:

- Actual Jan–Jul recovery, contacted book: **₹336.2M**
- Counterfactual without the change: **₹335.7M (−0.14%), ±1SE band ±0.27%**
this figure nets the switchers' post-period effect against the full 7-month, whole-universe total, which understates precision — the statistically-indistinguishable-from-zero conclusion is robust (confirmed independently by the event study showing no kink), but treat −0.14% itself as approximate rather than exact.
- Contribution of the strategy change: **~ −0.1% of recovery, not statistically significant**; the 18.6% book decline persists without the change.

Cross-check that anchors the sigh of relief: **accounts never targeted under any strategy version** (the purest "no change" group possible) declined **−18.8%** over the same months. The decline simply is not a product of the targeting strategy at all.

## Limitations

1. **Low statistical power.** Exposure is only ~8% of contacted account-months and payments are sparse/lumpy; the data can rule out a *large* effect but cannot distinguish small effects from zero. The 2×2 CI is ±0.27% of the contacted-book total — strong enough to reject the strategy as the cause of an 18.6% decline, not strong enough to certify a small true effect.
2. **No randomization.** Assignment to the new strategy is the operator's choice; while observable quality is balanced and account FE remove time-invariant selection, unobserved selection (e.g., accounts flagged "hard case" being moved to the new strategy) cannot be fully excluded.
3. **TWFE caveats.** With exposure concentrated in a minority of months, TWFE's β mixes sources of variation and can carry negative weights under heterogeneous effects; we therefore lead with the 2×2.
4. **Attribution ceiling (see Test 6).** Even a clean DiD here measures *account-level* effects of campaign exposure; mapping it to per-touch channel ROI is not possible — >78% of payments have no touchpoint within 30 days.
5. **Single 7-month window, one calendar year.** No seasonality, no later window, to confirm stability.
6. **Definition of treatment as v2/v3 = new.** The campaign file only carries 4 version labels; if "the change" the leadership is asking about is narrower than version ≅ strategy (e.g., channel mix, targeting rules), this analysis bounds its scope accordingly.

## Relationship to the executive memo

Consistent with the memo's "no driver found" conclusion, this analysis **formally attributes the −18.6% decline to the book/macro level (fewer payers, same per-payer amounts — see Test 4) and exonerates the strategy version change** as a cause: recovery without the mid-year change is statistically the same as recovery with it (±0.27%). The memo's recommendation (a capped randomized pilot) remains the right instrument to detect any *small* true effect this dataset cannot resolve.