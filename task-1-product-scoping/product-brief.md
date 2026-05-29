# Product Brief — Internal Marketing Performance Tool

**Author:** Dhanush Kumar  
**Version:** v1 scoping  
**Date:** May 2026

---

## Section 1 — Problem Statement

Marketing teams at agencies supporting multiple client brands face a recurring operational problem: answering the question "how is our marketing performing right now?" requires opening four or five separate tools, pulling figures manually, reconciling date ranges, and assembling a view that exists nowhere in a single place. The real cost of this is not the time it takes — it is what the manual process produces.

First, the output is inconsistent. Two analysts running the same check on the same day will look at different metrics, apply different filters, and reach different conclusions, with no record of how either arrived at their answer. Second, the process is person-dependent. The analyst who knows which tool to open for which client, and which numbers to trust, becomes a single point of failure. When that person is unavailable, the knowledge goes with them. Third, the latency between "something is underperforming" and "someone acts on it" is measured in days, not minutes — because no one is watching a unified signal. Fourth, and most invisibly, the manual process encodes priority judgments: whoever runs the check decides unconsciously what to look at first, which means the same data produces different decisions depending on who is in the room that day.

The tool exists to make that entire process unnecessary.

---

## Section 2 — Primary User

**The primary user for v1 is the internal analyst or account manager.**

This is a deliberate call. The temptation is to build for both internal teams and client stakeholders simultaneously, but that is a UX conflict, not a feature set. An internal analyst needs information density, fast pattern recognition, and the ability to spot a problem before it becomes a client conversation. A client stakeholder needs narrative context, reassurance, and a presentation-ready format that explains what the numbers mean. These two needs pull the interface in opposite directions.

Building for both simultaneously means the analyst view is too simplified to be useful operationally, and the client view is too raw to be safe to share. v1 optimises entirely for the analyst. A client-facing view is a v2 decision, made with evidence from how the analyst actually uses v1.

---

## Section 3 — The Core Question

The question, as a user would ask it:

> *"How is our marketing performing across channels this week, and which channel needs my attention right now?"*

A genuinely good answer to this question does three things:

1. **It shows the right scope.** Not all channels, all metrics, all time ranges simultaneously. It defaults to the last 30 days with week-over-week change, because that is the window where an analyst can act on what they see. Anything older is historical context; anything shorter is noise.

2. **It surfaces the signal, not just the data.** The answer is not a table of numbers. It is a ranked view that makes it obvious which channel has degraded, by how much, and relative to what baseline. The analyst should be able to walk into a client call knowing the answer without having performed any mental arithmetic.

3. **It tells you what you can act on.** The user walks away with one clear next action: "Paid social spend on Meta is down 18% week-over-week while LinkedIn is up 12% — investigate Meta creative fatigue." That is what a good answer looks like. A table of impressions and clicks is not.

---

## Section 4 — v1 Feature Set

The tool does exactly five things in v1. Nothing else.

1. **Channel performance overview with week-over-week change indicators.** Displays the last 30 days of performance for each connected channel — Google (paid + organic), Meta, LinkedIn, and HubSpot — with a directional indicator (up/down/flat) and percentage change per metric, per channel, for the current week versus the prior week.

2. **Unified metric table across channels.** A single table showing impressions, clicks, spend, conversions, and ROAS for all channels in one view. No switching between tabs or tools. Columns are consistent regardless of channel, with nulls shown explicitly where a channel does not report a given metric.

3. **Threshold-based attention flags.** Any channel where a key metric has dropped more than 15% week-over-week is automatically flagged with a visual indicator. The threshold is configurable at the admin level. This gives the analyst an immediate signal about where to look first, without requiring them to scan every row.

4. **Data freshness display per source.** Every metric on screen shows the timestamp of its most recent data pull. If a source has not refreshed within 26 hours, the metric is greyed out with a "stale data" label. If a source has failed entirely, the channel row shows "data unavailable" rather than a blank or a zero.

5. **Flat-file export of the current view.** The analyst can export the current dashboard view as a CSV with a single click. Column headers match what the analyst would use in a client slide. This removes the need to manually copy figures into a spreadsheet before a presentation.

---

## Section 5 — Data Sources and Flow

**Assumed data sources** (stated as assumptions — these would be confirmed in discovery):

| Source | What it provides |
|---|---|
| Google Analytics 4 | Organic traffic, conversions, engagement |
| Google Ads | Paid search spend, clicks, impressions, ROAS |
| Meta Ads Manager | Paid social spend, reach, conversions |
| LinkedIn Campaign Manager | B2B paid social spend, lead gen metrics |
| HubSpot | CRM conversion data, lead-to-close rates |

**Data flow:**

```
[GA4] ──────────────────────────────────────┐
[Google Ads] ───────────────────────────────┤
[Meta Ads Manager] ─────────────────────────┼──► [Scheduled API pulls, daily 5am]
[LinkedIn Campaign Manager] ────────────────┤         │
[HubSpot CRM] ──────────────────────────────┘         │
                                                       ▼
                                              [BigQuery — raw layer]
                                                       │
                                                       ▼
                                          [BigQuery — transformed views]
                                          (SQL views normalising schemas)
                                                       │
                                                       ▼
                                         [Dashboard — internal web app]
                                                       │
                                                       ▼
                                      [Analyst views, applies filters, exports]
```

The ingestion layer uses scheduled API pulls — one job per source, running daily at 5am before the working day starts. Each job writes to a dedicated raw table in BigQuery. Transformation happens in SQL views layered on top of the raw tables, normalising schema differences between sources into a single unified schema. The dashboard reads from the transformed views, never from raw tables directly.

Manual upload is available as a fallback for any source where API access is unavailable. The upload interface accepts a CSV with a defined template; the data is validated against the expected schema before being written to BigQuery.

---

## Section 6 — Why a User Would Trust This

An analyst presenting data to a client is staking their credibility on the accuracy of what they're showing. Trust in this tool is not a nice-to-have — it is the precondition for it being used at all.

The tool earns trust through four mechanisms:

**Data freshness is explicit.** Every metric on screen shows the exact timestamp of its last successful data pull, formatted as "Last updated: [date] at [time] from [source]." The analyst never has to wonder whether the number on screen reflects today's data or yesterday's.

**Every metric is labelled by source.** A clicks figure from Google Ads looks identical to a clicks figure from LinkedIn in raw form. The dashboard labels every metric with its originating source so the analyst knows exactly what they are presenting and can answer the question "where does that number come from?" without guessing.

**Stale and missing data is shown, never hidden.** If a data pull has not run in more than 26 hours, the metric is visually greyed out and labelled "stale — last updated [timestamp]." If a source has failed, the row shows "data unavailable" with a note that the issue is being investigated. A blank cell or a zero would be worse — both suggest the data exists and is fine, which is a lie.

**The tool does not backfill or interpolate.** If data is missing, it is missing. The tool never fills gaps with estimates or prior-period values, because a wrong number presented with confidence is worse than an acknowledged gap. This is a deliberate design position.

---

## Section 7 — Explicit v1 Exclusions With Reasoning

**1. Client-facing view.**  
Building a client view requires a fundamentally different design: narrative framing, contextual explanations, brand-safe formatting, and careful decisions about which raw numbers to expose versus abstract. That is a separate product. Attempting to serve both audiences with one interface would compromise both.

**2. Natural language querying.**  
"Show me our best-performing campaign last quarter" sounds useful, but it requires a robust semantic layer, campaign taxonomy standardisation, and significant LLM integration work. The core question does not require this. It adds complexity and a potential failure mode without solving the stated problem.

**3. Cross-brand benchmarking.**  
Comparing performance across client brands requires normalised spend figures, industry-specific baselines, and careful handling of confidentiality between accounts. That normalisation work is not trivial, and the assumptions required would make the comparison misleading without proper validation. This is a v3 problem.

**4. Automated recommendations engine.**  
Generating a recommendation like "reduce Meta spend and reallocate to LinkedIn" requires historical performance baselines, understanding of campaign objectives, and context about client strategy that the tool cannot hold. A recommendation produced without that context is worse than no recommendation — it creates false confidence in a suggested action.

**5. Historical trend analysis beyond 90 days.**  
Ninety days covers the most actionable decision window for a marketing analyst. Extending to 12 months significantly increases BigQuery storage costs, query complexity, and UI design requirements. It also shifts the tool from "operational monitoring" to "strategic reporting," which is a different product. This limit is a deliberate scope decision, not a technical constraint.

---

## Section 8 — v1 Success Metric

**An analyst can answer the core channel performance question — which channels are performing, which need attention, and why — in under 2 minutes, without opening any external tool.**

This is the only metric that matters for v1. If it takes longer than 2 minutes, or if the analyst has to cross-reference anything outside the tool to trust the answer, v1 has not worked.

---

## Section 9 — What I Would Revisit With More Time

**The primary user call.** I chose the internal analyst over the account manager, but I made that call without knowing how these roles actually divide in practice at a marketing technology company. At some agencies, account managers are the ones presenting to clients and need the tool themselves. At others, they delegate entirely to analysts. One week of user interviews would tell me whether I have the right primary user, or whether the analyst and account manager are in fact the same person.

**The 30-day default window.** Thirty days felt right as a default, but different channels have different conversion cycles. LinkedIn B2B campaigns often have 60-90 day sales cycles, which means a 30-day view systematically underrepresents LinkedIn's contribution. I made a simplifying assumption here that I would want to validate channel by channel.

**The 15% flag threshold.** I picked 15% week-over-week as the attention threshold because it felt high enough to avoid constant noise but low enough to catch real degradation. This is a coin flip. The right threshold depends on how volatile the channels typically are, and that varies by client, by industry, and by campaign type. It should be configurable from day one, and the right default should come from looking at real historical variance data.

**Whether HubSpot is the right CRM assumption.** I assumed HubSpot because it is the most common CRM at marketing agencies, but some agencies use Salesforce, some use Pipedrive, and some use spreadsheets. The abstraction layer for CRM data would need to be designed for swappability, not locked to HubSpot's specific API shape.
