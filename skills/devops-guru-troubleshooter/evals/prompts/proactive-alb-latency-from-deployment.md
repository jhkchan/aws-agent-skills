# Eval: proactive-alb-latency-from-deployment

**Difficulty:** hard
**Branch:** ROOT_CAUSE_FOUND — change-correlation identifies CodeDeploy deployment as the proximate root cause; rollback recommended

## Prompt

Diagnose this DevOps Guru insight:
Insight ID: x-1234abcd in us-east-1
describe-insight: PROACTIVE, HIGH, OPEN, Name="Increased latency
on ALB app/my-alb", StartTime=2026-08-09T14:35Z.
list-anomalies-for-insight: Anomaly "TargetResponseTime"
source AWS/ApplicationELB, p99 elevated from 200ms baseline to
1800ms starting 14:35Z. Secondary anomaly: AWS/RDS
DatabaseConnections elevated from 50 to 380 (connection pool
exhaustion), CPUUtilization 92%.
list-recommendations: AGGREGATE_OF_METRICS — "Investigate the
backend service for increased processing time."
CloudTrail: CodeDeploy deployment event at 2026-08-09T14:32Z,
application=my-app, revision=abc123.
Region: us-east-1.
