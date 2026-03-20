# SentryFlow Agent Context

## Project Overview
SentryFlow is a self-healing DevOps agent flow built on the GitLab Duo Agent Platform.
It combines pipeline self-healing and production incident response into a unified
four-agent architecture: Sentinel → Diagnostician → Surgeon → Reporter.

## Architecture
- Four agents connected via a custom flow: Sentinel → Diagnostician → Surgeon → Reporter
- Dual-trigger: GitLab pipeline failures and GCP Cloud Monitoring alerts
- Both triggers produce a unified incident schema consumed by downstream agents
- Decision gate after Diagnostician routes to: code fix, rollback, infra action, or issue-only

## Coding Conventions
- All agent outputs must be valid JSON conforming to the unified incident schema
- Branch naming: `sentryflow/fix-{description}` or `sentryflow/rollback-{commit-sha-short}`
- MR descriptions must include: root cause category, severity, confidence level, and GCP context
- Agent-generated commits must have clear, descriptive messages prefixed with `[SentryFlow]`
- No third-party secrets or credentials should appear in any agent output

## Unified Incident Schema
All agents communicate using this JSON schema:
```json
{
  "trigger_type": "pipeline_failure | gcp_alert",
  "project_id": "<gitlab-project-id>",
  "timestamp": "<ISO-8601>",
  "severity": "P1 | P2 | P3 | P4",
  "failure_context": {
    "source": "pipeline | gcp_monitoring",
    "pipeline_id": "<id or null>",
    "job_id": "<id or null>",
    "job_name": "<name or null>",
    "stage": "<stage or null>",
    "failure_message": "<extracted error>",
    "alert_policy_name": "<name or null>",
    "metric": "<metric or null>",
    "threshold": "<value or null>",
    "resource": "<resource identifier or null>",
    "raw_payload": {}
  }
}
```

## Failure Categories
Diagnostician classifies failures into:
- **test_failure** — unit/integration test assertion failed
- **dependency_issue** — package version conflict, missing dep, breaking update
- **config_error** — .gitlab-ci.yml syntax, env var missing, wrong image
- **infra_timeout** — job exceeded timeout, runner resource exhaustion
- **permission_error** — access denied, token expired, registry auth failed

## Confidence Levels
- **high** — clear root cause identified, auto-fix MR recommended
- **medium** — probable root cause, fix MR created with review warning
- **low** — uncertain diagnosis, create issue only for human triage

## Severity Levels
- **P1** — Production down, all pipeline stages failing, critical service unavailable
- **P2** — Multiple test failures, elevated error rates, dependency breakage
- **P3** — Single test failure, non-critical job failure, resource warnings
- **P4** — Informational alerts, allowed failures, minor warnings

## GCP Integration
- Cloud Monitoring alerts arrive via Pub/Sub as JSON payloads
- Cloud Logging is queried via `gcloud` CLI through the `run_command` tool
- BigQuery is used for audit trail logging
- All GCP commands use the project configured in the environment
- Never expose service account keys; rely on ambient credentials

## File Organization
- `skills/` — SKILL.md files for reusable agent patterns
- `.gitlab/duo/` — Agent and flow configuration
- `agents/` — Agent system prompts for GitLab UI reference
- `examples/` — Sample payloads for testing
- `docs/` — Architecture and setup documentation
