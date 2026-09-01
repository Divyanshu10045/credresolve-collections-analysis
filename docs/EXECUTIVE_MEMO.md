# Executive Memo: Collections Recovery Performance Review

**To:** Leadership Team | **Re:** Is recovery really up 11%, and where should the ₹10 Cr go?

## What happened?

**The reported "11% month-on-month improvement" is not a real trend.** It traces to a single volatile month (Feb→Mar 2026: raw recovery rose 10.99%) that was reported as if it represented ongoing performance. Looking at the full 7-month window of actual activity data (Jan–Jul 2026; August is a truncated partial month and excluded from trend analysis):

- **Raw/unaudited recovery**: essentially flat, -0.45% overall, average +0.21%/month
- **After removing duplicate payment records**: recovery actually **declined 18.6%** over the period, averaging -3.13%/month
- **Recovery per account touched and per agent-hour both declined ~19%** Jan→Jul — the clearest, most trustworthy signal in the data, since it's built entirely from payments' own internal amount/date fields rather than any cross-table status label

Duplicate payment records (two independent "SUCCESS" confirmations for the same transaction reference) inflate naive recovery totals by a consistent **~14.3% every month** — a real problem, but a flat one, so it doesn't manufacture the appearance of a trend on its own.

## Why did it happen?

We tested every driver on the list that this data can actually support: **risk segment, DPD, telephony vendor, campaign channel, strategy version, and attempt frequency.** None show a meaningful effect on contact rate (flat 19.3%–20.7% everywhere) or recovery rate (flat 10.5%–11.4% everywhere). This is a genuine negative finding, not a gap in the analysis — we checked both raw amounts and denominator-normalized rates.

Three drivers on the original list — **geography, language, and agent tenure** — could not be tested at all. Both `agents.csv` and `borrowers.csv` have their descriptive attributes (name, team, vendor, city, tenure) statistically decoupled from the ID field itself: a single `agent_id` shows a different name and team on nearly every row. We're not confident enough in these tables to draw conclusions from them, and recommend the source systems be audited before they're trusted for any reporting.

**What we found instead:** the funnel's top (getting someone on the phone) is stable; something downstream of contact is degrading. We traced one likely contributor — **promises-to-pay marked "KEPT" don't reliably correspond to actual payments.** Only 41% of accounts with a "KEPT" PTP have *any* successful payment ever recorded, at any date. If PTP-kept-rate has been used as an operational health metric, it's been tracking something close to noise, not real repayment behavior.

## How confident are we?

High confidence the 11% claim is false as a trend statement, and that duplicate payments inflate reported totals by ~14%. Moderate confidence in the "no driver found" result — it's consistent across every dimension we could test with clean data. Low confidence in any channel-attribution or ROI number below, because **85% of successful payments have no traceable touchpoint in any channel within 5 days beforehand** — most recovery in this dataset cannot be causally tied to any specific outreach action.

## What should we do, and what's the expected financial impact?

**Recommendation: WhatsApp/Digital Engagement — but as a capped pilot, not the full ₹10 Cr up front.**

Among the 15% of payments that *are* attributable to a channel, recovery-per-touch is nearly identical across calls, WhatsApp, SMS, and field visits (₹758–810). Given digital channels cost a fraction of a call or field visit per touch, this makes digital the best return-per-rupee direction *if* the correlational signal holds up causally — but we don't yet know that it does, and complaint rates are flat across channels (no backlash penalty either way).

- **Estimated incremental recovery (12 months, ~150,000 additional touches):** naive/correlational estimate ₹11.4 Cr; causally-adjusted range **₹2.3–4.5 Cr** (we assume only 20–40% of the correlational per-touch figure reflects true causal lift, given the attribution gap above)
- **Estimated cost:** raw messaging cost is trivial (~₹1.1 lakh); the ₹10 Cr is effectively a platform/capability investment (AI-driven conversational engagement, WhatsApp Business API + DND compliance, content/personalization, holdout-experiment infrastructure, a 12-month team)
- **Break-even:** likely **not achieved in Year 1 under the conservative causal estimate** (₹2.3–4.5 Cr recovery vs ₹10 Cr spend); only the naive/optimistic case clears breakeven, and that case is the one we trust least
- **Key assumption:** current per-touch effectiveness holds at scale — this is the single riskiest assumption, given both diminishing returns from over-contacting the same borrowers and the possibility that a large share of the observed correlation is reverse-causation (people who were going to pay anyway also get reminded)
- **Downside scenario:** if true causal lift is near zero, the full ₹10 Cr platform spend would show no measurable recovery impact
- **Confidence:** Low-to-moderate given the attribution gap — wide enough that we do not recommend committing the full amount without validating it first

**Concretely: fund a ~₹1–1.5 Cr randomized holdout pilot for 2–3 months** (a defined % of the portfolio receives no incremental digital outreach) to measure *true* incremental lift, before committing the remaining ~₹8.5–9 Cr. This directly answers the open question the correlational data can't: whether digital engagement is actually causing recovery, or just correlated with it.
