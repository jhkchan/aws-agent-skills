# Eval prompt: low-ri-coverage-steady-state

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: low-ri-coverage-steady-state)
Cost Explorer: enabled
Account spend profile: $20,000/month (steady-state EC2)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/org-imm
    MonitorName: org-imm
    MonitorType: IMMEDIATE
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::111111111111:anomalySubscription/finops
    SubscriptionName: finops-alerts
    Threshold: 100.0
    Frequency: IMMEDIATE
    MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/org-imm
    Subscribers: [{Address: finops@corp.com, Type: EMAIL}]
RI coverage (7-day avg): 22% (over $18,000 eligible EC2 spend)
SP coverage (7-day avg): 12% (over $18,000 eligible EC2 spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no
