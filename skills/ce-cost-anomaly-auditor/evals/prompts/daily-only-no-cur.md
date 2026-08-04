# Eval prompt: daily-only-no-cur

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: daily-only-no-cur)
Cost Explorer: enabled
Account spend profile: $8,000/month (EC2-heavy)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/daily-all
    MonitorName: daily-all
    MonitorType: DAILY
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::111111111111:anomalySubscription/daily-sub
    SubscriptionName: daily-sub
    Threshold: 50.0
    Frequency: DAILY
    MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/daily-all
    Subscribers: [{Address: finops@corp.com, Type: EMAIL}]
RI coverage (7-day avg): 68% (over $6,500 eligible EC2 spend)
SP coverage (7-day avg): 55% (over $6,500 eligible compute spend)
CUR v2 with IncludeResourceIDs: NOT configured (no resource-level cost data)
Free-tier: no
