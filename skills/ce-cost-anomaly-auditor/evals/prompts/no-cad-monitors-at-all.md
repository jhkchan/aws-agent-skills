# Eval prompt: no-cad-monitors-at-all

Audit the following AWS Cost Explorer configuration for FinOps posture.
Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account id: 111111111111 (label: no-cad-monitors-at-all)
Cost Explorer: enabled
Account spend profile: $12,000/month (EC2-dominant, steady-state)
Cost Anomaly Detection monitors: [] (zero monitors)
Cost Anomaly Detection subscriptions: [] (zero subscriptions)
RI coverage (7-day avg): 78% (over $9,000 eligible EC2 spend)
SP coverage (7-day avg): 65% (over $9,000 eligible EC2/Fargate spend)
CUR v2 with IncludeResourceIDs: enabled (Athena-integrated)
Free-tier: no (production account)
