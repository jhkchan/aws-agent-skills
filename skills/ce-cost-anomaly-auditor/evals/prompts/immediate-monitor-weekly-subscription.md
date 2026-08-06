# Eval prompt: immediate-monitor-weekly-subscription

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: immediate-monitor-weekly-subscription)
Cost Explorer: enabled
Account spend profile: $20,000/month (steady-state EC2/Fargate)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-prod
    MonitorName: imm-prod
    MonitorType: IMMEDIATE
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::111111111111:anomalySubscription/weekly-digest
    SubscriptionName: weekly-digest
    Threshold: 100.0
    Frequency: WEEKLY
    MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-prod
    Subscribers: [{Address: finops@corp.com, Type: EMAIL}]
RI coverage (7-day avg): 82% (over $16,000 eligible compute spend)
SP coverage (7-day avg): 75% (over $16,000 eligible compute spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no
