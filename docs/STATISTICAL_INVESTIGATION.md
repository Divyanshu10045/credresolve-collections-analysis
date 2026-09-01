# Statistical Investigation: Are the Reported Numbers Real?

**Status:** Final | **Source of truth:** `golden_dataset/*` (deduplicated) + `data/*`
**Reference period:** Jan–Jul 2026 (7 full months); August excluded as a truncated partial month
**Evidence labels:** **Fact** (direct data) · **Strong Evidence** (transparent, converging analysis) · **Correlation** (no causal claim) · **Hypothesis** (cannot be resolved with available data)

Companion scripts: `notebooks/06_statistical_investigation.py` (all tests below), `notebooks/05*.py` (underlying exploration). Every test is implemented with pandas/numpy only — no black box.

---

## Bottom line

The **-18.6% decline** in golden (deduplicated) SUCCESS recovery Jan→Jul (₹180.68M → ₹147.02M) is real and it is **not** an artifact of:

- changing risk/loan/DPD **mix** of who pays (Test 1)  — **Strong Evidence**
- **cohort/vintage** composition of the book (Test 2) — **Strong Evidence**
- which accounts get **selected** into contact (Test 3) — **Strong Evidence**
- **Simpson's paradox** flipping the aggregate (Test 5) — **Strong Evidence**

It **is** explained by where in the funnel it happens, and two of the candidate explanations are supported:

- **Survivorship / accounting check (Test 4):** the decline is almost entirely a fall in the **number of paying accounts** (−19.8%), not in the amount each payer pays (per-paying-account recovery is flat, +1.4%). **Strong Evidence** of "fewer payers, not smaller payments."
- **Time-series artifacts (Test 7):** August is truncated to ~23% of a full month and must not appear in trend analyses; the celebrated "11% Feb→Mar improvement" is a month-length artifact (+7.8% raw, **−2.6% per-day**). **Fact.**

One thing the data cannot support at all:

- **Attribution-window bias (Test 6):** only 3.2% of successful payments have any call/WhatsApp/SMS/field-visit touchpoint within 1 day; 12.4% within 5 days; 21.1% within 30 days (and it saturates). **>78% of payments have NO recorded touchpoint in any channel in the 30 days before they occur.** Any "recovery from outreach X%" number is therefore chosen by the lookback window you pick, and is unverifiable. **Hypothesis** (attribution not measurable in this dataset).

---

## Test 1 — Mix effects: is the paying population changing?

**Method.** Monthly composition of the paying population (which accounts actually pay) by risk segment, loan type, and DPD bucket; plus direct standardization: re-weight each month's recovery by the **January risk-segment composition** to ask "what would the trend look like if nothing about who pays had changed?"

**Findings.**

|  | Jan | Feb | Mar | Apr | May | Jun | Jul |
|---|---|---|---|---|---|---|---|
| Actual recovery (₹M) | 180.68 | 159.44 | 171.93 | 153.86 | 154.34 | 145.40 | 147.02 |
| Mix-adjusted recovery (₹M) | 45.19 | 39.86 | 42.98 | 38.44 | 38.61 | 36.38 | 36.75 |
| Jan→Jul change, **actual** | | | | | | | **−18.6%** |
| Jan→Jul change, **mix-adjusted** | | | | | | | **−18.7%** |

The "mix-adjusted" figure above is a simplified reweighting (segment totals scaled by fixed Jan dollar-shares), not full direct standardization by rate — treat it as corroborating the composition-percentage table above, not as an independent test.

Composition varies by less than ~3pp month-to-month in every dimension (e.g., HIGH risk pays 22.8–27.0% of monthly volume; credit-card share 18.8–20.9%; 0–15 DPD 35.2–38.0%).

**Verdict: Strong Evidence — the decline is NOT compositional.** Holding the January paying mix fixed changes the trend from −18.6% to −18.7%. The decline happens *within* risk/loan/DPD groups, not because the mix shifted.

---

## Test 2 — Cohort effects: are newer accounts behaving differently?

**Method.** Recovery and paying-account counts by **vintage** (month the account was opened, 23 cohorts from 2024-01 to 2025-11) × calendar month; vintage share of the paying population over time.

**Findings.** Every vintage pays ₹5–9M/month into a stable ~90–110-account monthly pool. The vintage mix of the paying population is essentially static over the window (each cohort holds roughly 11–18% of paying accounts in every month; no cohort's share moves monotonically by more than ~4pp). The most-payers cohort per calendar month jumps around randomly rather than drifting toward new vintages.

**Verdict: Strong Evidence — no cohort effect.** Recovery behavior of old and new books is indistinguishable; the decline cannot be explained by newer cohorts paying differently.

---

## Test 3 — Selection bias: does who gets contacted change?

**Method.** Per-month contact **coverage** of the 30,000-account book (share of accounts with ≥1 call), split by risk segment and DPD. Plus recovery-per-touched-account — the efficiency metric — both unconstrained and on a **balanced panel of the same 3,522 accounts touched in both January and July.**

**Findings.**

| Contact coverage (% of book) | HIGH | LOW | MEDIUM | NPA |
|---|---|---|---|---|
| Jan | 34.7 | 34.4 | 34.7 | 33.9 |
| Jul | 34.5 | 33.6 | 34.4 | 34.6 |

Coverage is flat at ~31–35% in every segment and every month (same story for DPD buckets). However, **the identity of who gets contacted turns over hard**: 10,324 accounts touched in Jan vs 10,278 in Jul, with only 3,522 (34%) in common.

| Recovery per touched account (₹) | Jan | Feb | Mar | Apr | May | Jun | Jul |
|---|---|---|---|---|---|---|---|
| All touched accounts | 5,766 | 5,222 | 6,136 | 5,203 | 5,155 | 4,647 | 4,950 |
| Same 3,522 accounts (balanced) | 6.1k | — | — | — | — | — | 5.1k |

**Verdict: Strong Evidence that observable selection does NOT drive the trend**, and — importantly — the decline survives even inside a balanced panel of the *same* accounts (−16.8%). This is a within-account decline, not a story about who you happened to call. Two honest caveats: (i) ~2/3 of the touched pool is different each month — unobserved selection on account quality is possible; (ii) the memo's "~19% per-account-touched decline" is directionally confirmed but measured here at −14.2%/−16.8% depending on sample definition.

---

## Test 4 — Survivorship bias: are we looking at the right population?

**Method.** Compare what we would have concluded if we tracked only accounts present throughout (balanced payer panel) vs. the truth across the full population each month. Also split what happened to January payers who stopped paying.

**Findings.**

- Jan payers: 2,298 → Jul payers: 1,844 → both months: only **146** (6.4% of Jan payers). **93.6% of January's payers are not paying in July.**
- A balanced payer panel (146 accounts) covers only 6.6% of Jan and 7.8% of Jul recovery — conditioning on it would produce garbage (a two-month panel with near-zero Feb–Jun values).
- What actually happened to the 2,152 January payers who stopped: 524 **PAID** (fully settled), 553 **CLOSED**, 556 **WRITEOFF**, 519 **ACTIVE**. Roughly half *left* the population (paid/closed); a quarter were written off; a quarter are still active but not paying.
- The **full-population** (not survivorship-biased) per-paying-account recovery is *flat*: ₹78.6k in Jan → ₹79.7k in Jul (**+1.4%**). Within every risk segment the same: 74–80k ₹/payer, no segment trends down.

**Verdict: Strong Evidence (with a Fact-quality structural feature).** Survivorship bias would be **fatal** to any "track the same payers across months" analysis — 93.6% of the payer population turns over monthly and the surviving panel is 146 accounts. Doing it correctly (all paying accounts each month): **the decline is a decline in the number of payers (−19.8%), while the amount per payer is flat (+1.4%).** The ₹286M "lost" is the *count* of paying accounts, not shrinking payments.

---

## Test 5 — Simpson's paradox: does the aggregate reverse within segments?

**Method.** Compare the aggregate Jan→Jul change (−18.6%) with the change computed within each risk segment, and with recovery-per-paying-account within each segment.

**Findings.**

| Risk segment | Jan (₹M) | Jul (₹M) | Change |
|---|---|---|---|
| HIGH | 46.3 | 35.2 | **−24.0%** |
| LOW | 44.2 | 38.9 | **−11.9%** |
| MEDIUM | 45.9 | 38.7 | **−15.7%** |
| NPA | 44.2 | 34.2 | **−22.7%** |
| **Aggregate** | **180.7** | **147.0** | **−18.6%** |

**Verdict: Strong Evidence — no Simpson's paradox.** The aggregate sits squarely inside the range of within-segment changes (−11.9% to −24.0%); no segment goes up. Per-paying-account recovery is flat *within* every segment, confirming the Test 4 reading at granularity: smaller-paying populations, same per-payer amounts, everywhere.

---

## Test 6 — Attribution-window bias: can we credit outreach for payments?

**Method.** For a sample of 1,200 SUCCESS payments (Jan–Jul), check whether any call, WhatsApp, SMS, or field visit occurred within N days before the payment, for N ∈ {1, 2, 3, 5, 7, 14, 30}.

**Findings.**

| Window | Any touchpoint (%) |
|---|---|
| 1 day | 3.2 |
| 2 days | 6.1 |
| 3 days | 8.7 |
| 5 days | 12.4 |
| 7 days | 15.2 |
| 14 days | 21.1 |
| 30 days | 21.1 (saturates) |

Per-channel (5-day window): call 4.1%, WhatsApp 3.7%, SMS 3.0%, field visit 2.2%.

**Verdict: Hypothesis — attribution is NOT measurable in this dataset, and any channel-attribution number is an artifact of the chosen lookback window.** The reported share moves from 3% to 21% just by lengthening the window; **more than 78% of payments have no touchpoint at all within 30 days** (they are bank-autopay/self-initiated payments not driven by any recorded outreach). This is why the counterfactual work (see `COUNTERFACTUAL.md`) uses account-level exposure and grand trends rather than touch-to-payment matching.

---

## Test 7 — Time-series / calendar effects

**Method.** Month-length and truncation checks, weekday composition, daily profile, month-to-month calendar comparisons.

**Findings.**

- **August is truncated:** 484 SUCCESS payments vs. 2,119 median full month ≈ **23% of a month**; recovery ≈ 23% of a typical month. Including August in any trend ("Jan→Aug") mechanically understates recovery. **Fact.**
- The '11% improvement' claim, verified as **+10.99%** on the true raw/undeduplicated payments, is explained by two compounding artifacts, not one. First, duplicate SUCCESS payment records inflate raw totals by **+5.8% in January, rising to +29.4% by July** (pooled +16.2% Jan–Jul) — and because the inflation *grows over time*, it doesn't just sit idle: it is exactly why raw recovery looks flat (−0.45% Jan→Jul) while deduplicated recovery fell 18.6% (the ~14.3% flat figure in DATA_QUALITY_REPORT.md §1.2 predates the current files; see `golden_dataset/cleaning_impact_log.csv`). Second, on the deduplicated golden figures, Feb→Mar shows **+7.8%** raw growth, but Feb has 28 days and Mar has 31 — normalizing to per-day recovery flips this to **−2.6%**. Together, duplicate inflation plus the short-month effect fully account for a headline number that never reflected real improvement. **Fact.**
- Weekday recovery mix is stable (each weekday ≈ 11–17% of monthly volume every month), but **absolute level fell on every weekday** between Jan and Jul (e.g., Wednesday ₹28.5M → ₹25.9M; Friday ₹30.3M → ₹23.9M). No day-of-week redistribution is hiding the decline.
- Only one calendar year is available, so **seasonality cannot be tested — treat any seasonal claim as a Hypothesis.** Daily mean Jan–Jul is ₹5.23M/day recovering but drifting down into the July tail.

**Verdict: Fact for truncation and month-length adjustments (any trend analysis must use Jan–Jul and per-day or calendar-adjusted values); Hypothesis for seasonality (cannot be resolved with 7 months).**

---

## What follows

- The decline is a **volume/count** phenomenon at the payer level, robust across all risk segments and untouched by mix, cohort, or selection-on-observables.
- The **attribution gap means no per-touch ROI number in this dataset is trustworthy** — the executive memo's ₹11.4 Cr naive figure should be treated as unverifiable, and its causally-adjusted ₹2.3–4.5 Cr range kept.
- Whether the **mid-year targeting strategy change** contributed anything is formally tested in `docs/COUNTERFACTUAL.md` (scripts `notebooks/07_counterfactual_did.py`): it did not — recovery without the change is statistically indistinguishable from recovery with it, and the decline occurs identically in accounts never touched by any strategy version.