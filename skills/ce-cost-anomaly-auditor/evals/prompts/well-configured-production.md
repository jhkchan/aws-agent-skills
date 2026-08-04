# Eval prompt: well-configured-production

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: well-configured-production)
Cost Explorer: enabled
Account spend profile: $10,000/month (steady-state EC2/Fargate)
Cost Anomaly Detection monitors:
  - MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-org
    MonitorName: imm-org
    MonitorType: IMMEDIATE
Cost Anomaly Detection subscriptions:
  - SubscriptionArn: arn:aws:ce::111111111111:anomalySubscription/finops-imm
    SubscriptionName: finops-imm
    Threshold: 500.0
    Frequency: IMMEDIATE
    MonitorArn: arn:aws:ce::111111111111:anomalyMonitor/imm-org
    Subscribers: [{Address: finops@corp.com, Type: EMAIL}]
RI coverage (7-day avg): 85% (over $8,000 eligible EC2 spend)
SP coverage (7-day avg): 80% (over $8,000 eligible compute spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no
