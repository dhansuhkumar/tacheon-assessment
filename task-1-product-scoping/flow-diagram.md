# Flow Diagram — Marketing Performance Tool

This diagram shows the full data and user interaction flow for the internal marketing performance tool. Read it left to right, top to bottom: data originates at the sources, gets pulled on a schedule, lands in BigQuery, is transformed into a unified view, and surfaces to the analyst through a dashboard.

```mermaid
flowchart TD
    subgraph Sources["Data Sources"]
        GA4["Google Analytics 4\nOrganic traffic · conversions · engagement"]
        GAds["Google Ads\nPaid search · spend · ROAS"]
        Meta["Meta Ads Manager\nPaid social · reach · conversions"]
        LI["LinkedIn Campaign Manager\nB2B lead gen · sponsored content"]
        HS["HubSpot CRM\nLead-to-close rates · pipeline value"]
    end

    subgraph Ingestion["Ingestion Layer"]
        Sched["Cloud Scheduler\nDaily trigger — 5am"]
        Conn["API Connectors\nOne job per source\nTimeout + retry handling"]
        Upload["Manual CSV Upload\nFallback only — same schema\nrequired as API output"]
    end

    subgraph BQ["Storage Layer — BigQuery"]
        Raw["Raw Tables\nOne table per source\nAppend-only · no transformation"]
        Views["Transformed Views\nUnified schema across sources\nSQL views normalising field names\nand nulls"]
    end

    subgraph Presentation["Presentation Layer"]
        Dash["Internal Dashboard\nLast 30 days · WoW change\nThreshold flags · freshness labels"]
    end

    subgraph UserLayer["User Interaction"]
        Analyst["Internal Analyst / Account Manager\nViews dashboard · applies filters\nInvestigates flagged channels"]
        Export["CSV Export\nPresentation-ready flat file\nColumn headers match slide format"]
    end

    GA4 --> Conn
    GAds --> Conn
    Meta --> Conn
    LI --> Conn
    HS --> Conn

    Sched -->|"triggers daily"| Conn
    Upload -->|"writes directly on upload"| Raw

    Conn -->|"writes raw JSON → tabular"| Raw
    Raw -->|"read-only by views"| Views
    Views -->|"dashboard reads views only,\nnever raw tables"| Dash

    Dash --> Analyst
    Analyst -->|"one-click"| Export

    style Sources fill:#1e293b,color:#94a3b8,stroke:#334155
    style Ingestion fill:#1e293b,color:#94a3b8,stroke:#334155
    style BQ fill:#1e293b,color:#94a3b8,stroke:#334155
    style Presentation fill:#1e293b,color:#94a3b8,stroke:#334155
    style UserLayer fill:#1e293b,color:#94a3b8,stroke:#334155
```

---

## Design Decisions in This Diagram

**Why the dashboard reads views, not raw tables.**  
Raw tables accumulate every append. If the dashboard queried raw tables directly, a schema change in one source would break the dashboard query immediately. The transformation view layer acts as a contract: it absorbs schema changes and always presents the same interface to the dashboard.

**Why the manual upload writes to raw, not to views.**  
The upload goes through the same raw table so that the same transformation views apply. A separate ingestion path for manual data would create two sources of truth for the same metric.

**Why scheduling is external (Cloud Scheduler) rather than in-app.**  
Putting the schedule outside the pipeline means the pipeline itself is stateless and rerunnable. Cloud Scheduler can be paused, modified, or replaced without touching a single line of pipeline code. This also makes the transition to a more robust orchestrator (Airflow, Cloud Composer) trivial — you just point the trigger at a different endpoint.

**What is deliberately absent from this diagram.**  
There is no client-facing layer, no alerting layer, and no recommendation engine. These are v2+ decisions. The diagram shows only what v1 builds.
