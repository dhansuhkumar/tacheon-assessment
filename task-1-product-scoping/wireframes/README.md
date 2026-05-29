# Wireframe Descriptions — Marketing Performance Tool

These are written wireframe descriptions. Each is detailed enough for a designer to produce a working mockup without further input. Two screens cover the core v1 user journey: the overview, and the drill-down.

---

## Screen 1 — Main Dashboard

### Purpose

This is the first screen the analyst sees after logging in. It must answer the core question — which channels are performing, which need attention — without requiring any interaction. Everything visible on load should be useful.

### Layout

A single-column layout with a fixed top navigation bar and a scrollable content area below it. No sidebar. The content area is divided into three horizontal bands: a summary row, a channel table, and a footer bar. The layout is full-width on desktop (1280px minimum). Mobile is out of scope for v1.

### Top Navigation Bar

- Left: Product name ("PerfView" or equivalent) and the client selector — a dropdown populated with the analyst's assigned client accounts. Changing the client reloads all data on screen.
- Centre: Date range control. Default is "Last 30 days." Options: Last 7 days, Last 30 days, Last 90 days. Custom range is not in v1.
- Right: "Last refreshed" timestamp for the overall dashboard, formatted as "Data refreshed: 29 May 2026 at 05:12." A warning indicator (amber dot) appears here if any source is stale.

### Summary Row

Three metric cards in a horizontal row immediately below the nav bar. Cards show:
1. **Total spend** across all channels for the selected period, with week-over-week percentage change and directional arrow.
2. **Total conversions** across all channels, with week-over-week change.
3. **Blended ROAS** (total conversion value ÷ total spend), with week-over-week change.

Each card uses a green up-arrow for positive change and a red down-arrow for negative change. Flat is shown in grey. The percentage is always shown to one decimal place.

**UX decision:** Three summary cards, not five or ten. The analyst needs to orient themselves instantly on load. More cards create visual noise without improving the orienting question. The full breakdown is one scroll away in the channel table.

### Channel Performance Table

A table with one row per channel. Columns:

| Column | Description |
|---|---|
| Channel | Source name (Google Organic, Google Paid, Meta, LinkedIn, HubSpot) |
| Impressions | Total for period |
| Clicks | Total for period |
| Spend | Total spend (blank for organic) |
| Conversions | Total for period |
| ROAS | Spend ÷ conversion value (blank where not applicable) |
| WoW Change | Percentage change on the primary metric for that channel, with directional arrow |
| Flag | Amber warning icon if WoW change exceeds the negative threshold |
| Last Updated | Timestamp of most recent successful data pull for this channel |

Rows are sorted by flag status first (flagged rows appear at the top), then by spend descending. The analyst sees the problem rows immediately without scanning.

Clicking any row navigates to Screen 2 (channel drill-down) for that channel.

**UX decision:** Sorting flagged rows to the top, rather than highlighting them in place. Highlighting in a long table still requires visual scanning. Moving flagged rows to the top means the analyst's eyes go straight to what needs attention. This is the single most important interaction decision in v1.

**Data unavailability state:** If a source has failed entirely, its row shows "Data unavailable — source error" in place of all metric cells, with a grey background. The row does not show zeros. Zeros imply the metric is real and the number is zero. A failed pull is a different situation and must be communicated differently.

### Footer Bar

A thin bar at the bottom of the content area showing:
- "Powered by data from: Google Analytics 4 · Google Ads · Meta · LinkedIn · HubSpot"
- A link to the data freshness detail view (out of scope for v1, placeholder only)
- "Export current view" button — generates and downloads the current table as a CSV

---

## Screen 2 — Channel Drill-Down

### Purpose

The analyst has clicked a channel row on the main dashboard. This screen gives them enough detail to understand why that channel is performing the way it is — not to do a full analysis, but to walk into a client conversation prepared.

### Layout

Two-column layout below the navigation bar. Left column (60% width): time-series chart and campaign breakdown table. Right column (40% width): metric summary panel and data freshness detail.

### Navigation

A breadcrumb at the top left: "Dashboard > [Client Name] > [Channel Name]" with the "Dashboard" segment as a clickable back link. No browser back-button dependency.

### Left Column — Time Series Chart

A line chart showing the primary metric for the selected channel over the selected date range. Default metric is the most relevant for that channel (ROAS for paid channels, sessions for organic). The analyst can switch the metric using a dropdown above the chart.

The chart shows:
- Current period line (solid)
- Prior period line (dashed, same date range shifted back by one period) for direct visual comparison
- A horizontal reference line at the week-over-week threshold (the value where the flag would trigger), shown in amber

**UX decision:** Showing the prior period line on the same chart rather than in a separate comparison panel. When the two lines diverge visibly, the analyst immediately sees when the degradation started — which is the question they actually need to answer before the client call.

### Left Column — Campaign Breakdown Table

Below the chart: a table showing performance by individual campaign within the channel. Columns: Campaign Name, Impressions, Clicks, Spend (if applicable), Conversions, ROAS (if applicable). Rows sorted by spend descending.

This table is the key investigative tool. If the channel metric has dropped, this table tells the analyst which campaign is responsible.

No click-through from this table in v1. It is read-only.

### Right Column — Metric Summary Panel

A vertical stack of metric cards:
- Current period total for each metric available from this channel
- Week-over-week change with directional indicator
- A "vs. same period last month" comparison (if 90-day data is selected; blank for 7-day and 30-day views)

This panel stays fixed while the analyst scrolls through the campaign table.

### Right Column — Data Freshness Detail

Below the metric summary: a small panel showing:
- Source name
- Last successful pull: date and time
- Pull frequency: daily at 5am
- Status: "Current" (green) or "Stale — [X] hours old" (amber) or "Source error" (red)
- If stale or errored: a note explaining what the analyst should do ("Contact your data administrator")

**UX decision:** Putting data freshness in the right column of the drill-down rather than only in the main table. An analyst on this screen is about to use these numbers in a conversation. They need freshness information in front of them at this moment, not buried in the overview. Seeing "last updated 2 hours ago" next to the numbers they are about to quote is the reassurance that makes the tool trustworthy.
