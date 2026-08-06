# Eval prompt: monitors-no-subscriptions

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: monitors-no-subscriptions)
Cost Explorer: enabled
Account spend profile: $8,000/month (mixed EC2/Fargate)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-prod
    MonitorName: imm-prod
    MonitorType: IMMEDIATE
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/daily-prod
    MonitorName: daily-prod
    MonitorType: DAILY
Cost Anomaly Detection subscriptions: [] (zero subscriptions)
RI coverage (7-day avg): 72% (over $6,000 eligible compute spend)
SP coverage (7-day avg): 60% (over $6,000 eligible compute spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no
