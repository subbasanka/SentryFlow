# GCP Setup Guide for SentryFlow

## Prerequisites
- A Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and authenticated
- A GCP project (new or existing)

## Step 1: Enable Required APIs

```bash
gcloud services enable \
  monitoring.googleapis.com \
  logging.googleapis.com \
  pubsub.googleapis.com \
  bigquery.googleapis.com
```

## Step 2: Create Pub/Sub Topic and Subscription

Create a topic for Cloud Monitoring alerts:
```bash
gcloud pubsub topics create sentryflow-alerts
```

Create a subscription (push or pull depending on your integration approach):
```bash
# Option A: Pull subscription (for Cloud Function)
gcloud pubsub subscriptions create sentryflow-alerts-sub \
  --topic=sentryflow-alerts \
  --ack-deadline=60

# Option B: Push subscription (direct to webhook endpoint)
gcloud pubsub subscriptions create sentryflow-alerts-push \
  --topic=sentryflow-alerts \
  --push-endpoint=https://your-gitlab-webhook-endpoint \
  --ack-deadline=60
```

## Step 3: Create Cloud Monitoring Alert Policy

Create an alert policy that fires on error rate spikes:
```bash
gcloud alpha monitoring policies create \
  --display-name="SentryFlow - High Error Rate" \
  --condition-display-name="Error rate exceeds threshold" \
  --condition-filter='metric.type="logging.googleapis.com/user/error_count" AND resource.type="k8s_container"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=60s \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=<channel-id> \
  --combiner=OR
```

Configure the notification channel to publish to the Pub/Sub topic:
```bash
gcloud alpha monitoring channels create \
  --display-name="SentryFlow Pub/Sub" \
  --type=pubsub \
  --channel-labels=topic=projects/<project-id>/topics/sentryflow-alerts
```

## Step 4: Create BigQuery Dataset and Table

Create the audit trail dataset:
```bash
bq mk --dataset sentryflow_audit
```

Create the incidents table:
```bash
bq mk --table sentryflow_audit.incidents \
  timestamp:TIMESTAMP,trigger_type:STRING,project_id:STRING,root_cause_category:STRING,confidence:STRING,action_taken:STRING,mr_iid:INTEGER,issue_iid:INTEGER,resolution_time_seconds:INTEGER,severity:STRING,affected_services:STRING
```

## Step 5: Service Account Setup

Create a service account for SentryFlow:
```bash
gcloud iam service-accounts create sentryflow-agent \
  --display-name="SentryFlow Agent"
```

Grant required roles:
```bash
PROJECT_ID=$(gcloud config get-value project)

# Cloud Monitoring viewer (read alerts)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sentryflow-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"

# Cloud Logging viewer (read logs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sentryflow-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"

# Pub/Sub subscriber (receive alerts)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sentryflow-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

# BigQuery data editor (write audit logs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sentryflow-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

## Step 6: GitLab CI/CD Variables

Set these CI/CD variables in your GitLab project (Settings > CI/CD > Variables):

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `GCP_PROJECT_ID` | Your GCP project ID | Yes | No |
| `GCP_SERVICE_ACCOUNT_KEY` | Service account JSON key | Yes | Yes |
| `GCP_REGION` | e.g., `us-central1` | Yes | No |

## Step 7: Integration Bridge (Pub/Sub → GitLab)

To connect GCP alerts to the SentryFlow agent flow, use one of these approaches:

### Option A: Cloud Function (Recommended)
Create a Cloud Function triggered by the Pub/Sub topic that creates a GitLab issue comment mentioning the SentryFlow agent service account. This triggers the flow.

### Option B: Push Subscription
Configure a Pub/Sub push subscription that sends directly to a GitLab webhook endpoint.

## Testing the Integration

Inject a test log entry to trigger an alert:
```bash
gcloud logging write test-log \
  '{"message": "Test error for SentryFlow", "severity": "ERROR"}' \
  --severity=ERROR
```

Verify the alert fires and the Pub/Sub message is received.
