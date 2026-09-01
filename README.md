# CredResolve Collections Analytics — Data Analyst Assignment

## The headline answer

**The reported "recovery has improved by 11% month-on-month" is false as a trend claim.**
It matches one single volatile month (Feb→Mar 2026, naive MoM +10.99%) almost exactly, and
was reported as if it represented sustained performance. The real 7-month trend (Jan–Jul 2026;
August excluded as a truncated partial month) is **flat under the naive definition and declining
18.6% once duplicate payments are removed.** Recovery per account and per agent-hour both
declined ~19% over the same window — the most trustworthy signal in the dataset, since it's
built entirely from payments' own internal fields rather than a cross-table status label.

Full reasoning: [`docs/EXECUTIVE_MEMO.md`](docs/EXECUTIVE_MEMO.md) (2-page summary) and
[`notebooks/ANALYSIS_NOTEBOOK.ipynb`](notebooks/ANALYSIS_NOTEBOOK.ipynb) (full analysis with narration).

## Repo structure

```
docs/
  EXECUTIVE_MEMO.md          <- start here (2 pages, answers all 4 leadership questions)
  DATA_QUALITY_REPORT.md     <- every data issue found, how detected, how treated, impact
  ARCHITECTURE.md            <- production pipeline design (Raw -> Staging -> ... -> Dashboard)
notebooks/
  ANALYSIS_NOTEBOOK.ipynb    <- full reasoning + code, narrated
  01_profile.py .. 04_drivers.py   <- source scripts the notebook is built from
sql/
  01_golden_dataset.sql      <- reproducible cleaning logic as SQL views
  02_metrics.sql             <- all metric definitions + the headline 11%-check query
golden_dataset/
  *_golden.csv                <- cleaned analytical tables
  cleaning_impact_log.csv     <- raw -> kept -> rejected row counts per cleaning step
dashboard/
  executive_dashboard.html    <- one-screen CEO view (open directly in a browser)
```

## Key findings, in order of importance

1. **11% claim is a single-month cherry-pick**, not a trend (see memo).
2. **`agents.csv` and `borrowers.csv` are unreliable dimension tables** — descriptive attributes
   (name, team, vendor, city, tenure) are statistically decoupled from the ID itself. Excluded
   from all analysis.
3. **No timezone signal exists anywhere in the data** — hour-of-day is flat across all 24 hours
   regardless of stated timezone, confirmed in both `calls` and `agent_sessions`.
4. **Duplicate payments inflate reported recovery by a constant ~14.3%/month** — real, but not
   trend-driving since the rate doesn't change over time.
5. **No tested operational driver (risk segment, DPD, vendor, channel, attempt frequency)
   shows a meaningful effect** on contact rate or recovery rate — a genuine negative result.
6. **PTP "KEPT" status doesn't reliably correspond to actual payment** — only 41% of accounts
   with a kept PTP have any successful payment ever recorded.
7. **85% of successful payments have no attributable touchpoint** in any channel within 5 days —
   channel ROI claims in this dataset are necessarily low-confidence.
8. **₹10 Cr recommendation: WhatsApp/Digital Engagement, as a capped pilot** (~₹1-1.5 Cr holdout
   experiment) rather than a full up-front commit, given finding #7.

## How to reproduce

```bash
python3 notebooks/01_profile.py          # initial data profiling
python3 notebooks/02_golden_dataset.py   # builds golden_dataset/*.csv + cleaning_impact_log.csv
python3 notebooks/03_metrics.py          # rate-based metric definitions
python3 notebooks/04_drivers.py          # driver analysis across risk/DPD/vendor/channel/attempts
```

Or open `notebooks/ANALYSIS_NOTEBOOK.ipynb` for the full narrated walkthrough.
For the SQL-native equivalent, run `sql/01_golden_dataset.sql` then `sql/02_metrics.sql`
against tables loaded into a `raw` schema.
