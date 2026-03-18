# SentryFlow

**A Self-Healing DevOps Agent Flow for GitLab**
---

## Overview

SentryFlow is a unified self-healing DevOps agent flow built on the **GitLab Duo Agent Platform**. It combines two critical failure-response systems into a single four-agent flow:

- **Pipeline Self-Healing** — When a CI/CD pipeline fails, the agent automatically reads job logs, diagnoses the root cause, and opens a merge request with the fix.
- **Production Incident Response** — When a GCP Cloud Monitoring alert fires, the agent correlates the incident with recent deployments, identifies the suspect commit, and drafts a rollback MR.

Both failure modes flow through the same four-agent architecture:

```
Sentinel → Diagnostician → Surgeon → Reporter
```

---

## Architecture

### Four-Agent Design

| Agent | Role | Description |
|---|---|---|
| **Sentinel** | Event Ingestion & Routing | Listens for GitLab pipeline failure webhooks and GCP Cloud Monitoring alerts via Pub/Sub. Normalizes both into a unified incident schema and routes to the Diagnostician. |
| **Diagnostician** | Root Cause Analysis | For pipeline failures: parses job logs and identifies failure category (test, dependency, config, infra). For production incidents: correlates incident timestamp with recent deployments and commits, pulls GCP Cloud Logging context. |
| **Surgeon** | Fix Generation & Action | Based on diagnosis, takes one of four actions: code/config fix MR, rollback MR, infra remediation + issue, or issue-only for low-confidence cases. |
| **Reporter** | Communication & Audit | Posts structured incident summary to MR/issue with root cause, affected services, fix applied, confidence level, and GCP log links. Logs event to BigQuery for historical analysis. |

### Flow Orchestration

```
Trigger → Sentinel → Diagnostician → Decision Gate → Surgeon → Reporter → End
```

The **Decision Gate** routes to one of four paths based on the Diagnostician's analysis:

- **Code Fix** — Test failure, dependency issue, or config error → generate fix and open MR
- **Rollback** — Bad production deploy → revert the suspect commit via MR
- **Infra Action** — GKE/resource issue → create issue with remediation steps
- **Issue Only** — Low confidence diagnosis → create structured issue for human triage

### Dual-Trigger Architecture

**Trigger A — Pipeline Failure:**
```
GitLab webhook → Sentinel (extracts job ID) → Diagnostician (reads job logs)
  → categorizes failure → Surgeon (generates fix) → opens MR on new branch
```

**Trigger B — Production Incident:**
```
GCP Cloud Monitoring alert → Pub/Sub → Sentinel (normalizes alert payload)
  → Diagnostician (correlates with recent deploys) → identifies suspect commit
  → Surgeon (drafts rollback MR or creates remediation issue)
```

---

## Google Cloud Integration

| GCP Service | Priority | Role |
|---|---|---|
| **Cloud Monitoring** | Core | Production incident trigger. Alert policies detect error rate spikes, latency anomalies, or resource exhaustion. Alerts fire webhooks to Pub/Sub, triggering the Sentinel agent. |
| **Cloud Pub/Sub** | Core | Event routing layer. Bridges GCP alerts to the GitLab agent flow. |
| **Cloud Logging** | Core | Infrastructure context for diagnosis. Correlates pipeline/production failures with infrastructure events (e.g., GKE node OOM). |
| **BigQuery** | Enhancement | Audit trail and trend analysis. Logs every incident (trigger type, root cause, fix applied, resolution time). |
| **Error Reporting** | Enhancement | Grouped error context — affected users, first-seen time, and stack traces for richer diagnosis. |
| **GKE / Cloud Run** | Enhancement | Infrastructure remediation target. Surgeon can scale a GKE node pool or restart a Cloud Run service. |

---

## Platform Tools Used

| Tool | Used By / Purpose |
|---|---|
| `get_job_logs` | Diagnostician — read failed pipeline job output |
| `get_pipeline_errors` | Diagnostician — get logs for failed jobs from latest pipeline |
| `get_pipeline_failing_jobs` | Diagnostician — identify which jobs failed |
| `list_commits` | Diagnostician — find recent commits for deployment correlation |
| `get_commit` / `get_commit_diff` | Diagnostician — analyze suspect commit changes |
| `get_repository_file` | Diagnostician/Surgeon — read config files and source code |
| `list_repository_tree` / `find_files` | Surgeon — understand project structure for fix generation |
| `create_file_with_contents` / `edit_file` | Surgeon — create or modify files for the fix |
| `create_commit` | Surgeon — commit fix/rollback to a new branch |
| `create_merge_request` | Surgeon — open MR with fix or rollback |
| `create_merge_request_note` | Reporter — post diagnosis summary to MR |
| `create_issue` | Surgeon/Reporter — create incident issue for tracking |
| `create_issue_note` | Reporter — post incident details to issue |
| `run_command` | Diagnostician — execute shell commands for GCP API calls |
| `blob_search` / `grep` | Diagnostician — search codebase for relevant context |

---

## Repository Structure

```
sentryflow/
├── README.md                           # Setup, architecture, usage
├── LICENSE                             # MIT License
├── AGENTS.md                           # Agent customization rules
├── .gitlab/
│   └── duo/
│       ├── agent-config.yml            # Flow execution config
│       └── mr-review-instructions.yaml # Custom review standards
├── skills/
│   ├── pipeline-diagnosis/
│   │   └── SKILL.md                    # Pipeline failure diagnosis skill
│   ├── incident-correlation/
│   │   └── SKILL.md                    # Deployment-incident correlation skill
│   └── gcp-integration/
│       └── SKILL.md                    # GCP API interaction patterns
├── docs/
│   ├── architecture.md                 # Detailed architecture doc
│   └── gcp-setup.md                    # GCP project setup guide
└── examples/
    ├── sample-pipeline-failure/        # Test fixtures for pipeline failures
    └── sample-gcp-alert/               # Sample Cloud Monitoring alert payloads
```

---

## Setup

### Prerequisites

- A GCP project with the following APIs enabled:
  - Cloud Monitoring
  - Cloud Logging
  - Cloud Pub/Sub
  - BigQuery

### GCP Setup

1. Enable required APIs in your GCP project:
   ```bash
   gcloud services enable monitoring.googleapis.com logging.googleapis.com pubsub.googleapis.com bigquery.googleapis.com
   ```
2. Create a Pub/Sub topic and subscription for Cloud Monitoring alerts.
3. Configure a Cloud Monitoring alert policy to publish to the Pub/Sub topic.
4. See [`docs/gcp-setup.md`](docs/gcp-setup.md) for detailed instructions.

### GitLab Agent Setup

1. Navigate to **Automate → Agents** in your GitLab project.
2. Create four custom agents: `sentinel`, `diagnostician`, `surgeon`, `reporter`.
3. Configure each agent with its system prompt and tool selections (see `skills/` directory).
4. Register the custom flow using the `flow.yaml` configuration file.
5. Configure a GitLab webhook for pipeline failure events pointing to the Sentinel agent.

---

## How It Works

### Pipeline Failure (Demo)

1. A commit breaks a test — the pipeline fails.
2. GitLab fires a webhook to the Sentinel agent.
3. Diagnostician reads the job logs and categorizes the failure.
4. Surgeon generates a fix and opens a merge request on a new branch.
5. Reporter posts a structured diagnosis comment on the MR.
6. Merge the MR — pipeline goes green.

### Production Incident (Demo)

1. An error rate spike triggers a GCP Cloud Monitoring alert.
2. The alert is published to Pub/Sub and received by Sentinel.
3. Diagnostician correlates the incident timestamp with recent deployments.
4. The suspect commit is identified using `list_commits` and `get_commit_diff`.
5. Surgeon drafts a rollback MR or creates a remediation issue.
6. Reporter posts the full diagnosis with GCP log links to the issue.

---

## Impact

| Metric | Before SentryFlow | After SentryFlow |
|---|---|---|
| Pipeline failure triage | 15–60 minutes per occurrence | Seconds |
| Production incident MTTR | 30 minutes to several hours | Seconds |
| Human effort required | Manual log reading + fix creation | Zero (automated) |

SentryFlow addresses the **"AI Paradox"** — AI tools generate code faster than ever, but the operational bottlenecks around that code remain manual. SentryFlow closes that gap.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
