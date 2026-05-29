# Task 1 — Product Scoping

**Author:** Dhanush Kumar

---

## What I Built and Why

This folder contains the v1 product scope for an internal marketing performance tool. The tool solves one problem: an analyst at a marketing agency currently has to open four or five separate platforms, pull numbers manually, and reconcile them before they can answer a question their clients ask every week. That process is slow, inconsistent, and depends on the knowledge of whoever happens to be running it.

I scoped a tool that replaces that process. The scope is deliberately narrow. A focused tool that solves one problem reliably is more useful than an expansive one that partially solves several.

The deliverables are:
- [`product-brief.md`](./product-brief.md) — the full product brief with 9 sections
- [`flow-diagram.md`](./flow-diagram.md) — a Mermaid.js diagram of the full data and interaction flow
- [`wireframes/README.md`](./wireframes/README.md) — written descriptions of the two core screens

---

## The One Framing Decision That Shaped Everything

Early in the scoping process I had to decide: who is this tool for?

The obvious answer is "both the internal team and the clients they serve." That answer leads to a tool that does not work well for either. An analyst needs information density, speed, and a clear signal about where to look. A client needs narrative, reassurance, and a presentation-ready format. These are different products wearing the same clothes.

I chose the internal analyst as the primary user. That single decision cascades into every other choice: the layout is dense rather than explanatory, the default is 30 days rather than a month-by-month narrative, the flags are threshold-based rather than AI-interpreted, and the export produces a flat CSV rather than a formatted PDF deck.

If I had picked the client as the primary user, every one of those decisions would have gone the other way. There is no version of this product that serves both users well in v1.

---

## What I Considered and Ruled Out

**Natural language querying.** Adding a "chat with your data" interface seems valuable but introduces a semantic layer that requires weeks of work to get right. The core question — how is performance this week — does not require it. It can be answered with a well-designed table.

**Cross-brand benchmarking.** Comparing performance across client accounts requires normalisation assumptions (industry baselines, spend scales, campaign types) that would take weeks to validate. An incorrect benchmark is worse than no benchmark — it misleads rather than informs.

**Automated recommendations.** A tool that says "move spend from Meta to LinkedIn" sounds compelling. A tool that says that without knowing the client's campaign strategy, their brand constraints, or their historical context is dangerous. I ruled it out not because it is technically hard but because it requires context the tool cannot hold.

**Historical data beyond 90 days.** Ninety days is the most actionable window for a performance analyst. Extending to a year changes the product from operational monitoring to strategic reporting — a different use case with different design requirements.

**Client-facing view.** See the primary user decision above. This is v2, not v1.

---

## What I Would Do Differently With More Time

**User interviews before scoping.** I made the analyst the primary user without speaking to any analysts. The right call may be obvious in hindsight, but it should have been validated before I committed to it. One week of five 30-minute interviews would have confirmed or overturned that decision with evidence.

**More specificity on the transformation layer.** I named SQL views as the transformation mechanism without specifying the exact schema normalisation logic. That normalisation — particularly for metrics that share a name across platforms but have different definitions (e.g. "conversions" means something different in Google Ads versus HubSpot) — is where most of the engineering risk lives, and I left it underspecified.

**A clearer staleness policy.** I defined "stale" as more than 26 hours since last pull, but I picked that number arbitrarily. The right threshold depends on how variable the data is day-to-day and what the consequences of presenting stale data are. I would have wanted to understand the team's client-presentation rhythm before setting that number.

---

## How to Read This Folder

Start with [`product-brief.md`](./product-brief.md). It explains the problem, the user, the features, and the decisions — including what was excluded and why. It is the most complete expression of the thinking behind this scope.

Then read [`flow-diagram.md`](./flow-diagram.md). The Mermaid diagram shows how data moves from source to analyst. The notes below the diagram explain the architectural decisions — specifically why the dashboard reads from views rather than raw tables, and why scheduling is external.

Then read [`wireframes/README.md`](./wireframes/README.md). The two screen descriptions are detailed enough for a designer to work from. Each screen includes a specific UX decision and the reasoning behind it — not just what the screen shows, but why it is structured the way it is.
