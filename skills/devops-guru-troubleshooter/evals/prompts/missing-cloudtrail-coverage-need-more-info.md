# Eval: missing-cloudtrail-coverage-need-more-info

**Difficulty:** medium
**Branch:** NEED_MORE_INFO — CloudTrail data events for Lambda NOT enabled; application logs NOT shipped; deployment history inaccessible

## Prompt

Diagnose this DevOps Guru insight:
Insight ID: w-3456mnop in us-east-1
describe-insight: PROACTIVE, MEDIUM, OPEN, Name="Increased
Lambda function duration for checkout-handler", StartTime=
2026-08-10T10:00Z.
list-anomalies-for-insight: AWS/Lambda Duration p99 elevated
from 800ms baseline to 4500ms starting 10:00Z; Errors slightly
elevated; Throttles=0.
list-recommendations: AGGREGATE_OF_METRICS — "Investigate the
Lambda function code."
Problem: CloudTrail data events for Lambda are NOT enabled in
this account. Application logs from the Lambda are NOT shipped
to CloudWatch Logs. We have no deployment history accessible.
Region: us-east-1.
