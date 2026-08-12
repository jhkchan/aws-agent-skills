# Eval prompt: critical-exception-list

Design a patch-compliance automation workflow for a fleet that includes
3 critical instances that must NOT be auto-patched. Emit the standard
PATCH block including the exception register.

Design reference: critical-exception-list
Account: 111111111111
Region: us-east-1

Fleet: 200 Amazon Linux 2023 instances (prod)
General fleet: 197 instances tagged "Patch Group" = "al2023-prod"
Critical exceptions (3 instances):
  - i-0db123prod: Primary database proxy, change-frozen until Q4 migration
  - i-0aux456legacy: Legacy app, patching breaks JCE provider
  - i-0mon789grafana: Monitoring server, patching requires coordinated restart
Desired approach: general fleet gets weekly Install; exceptions get
Scan-only via "Patch Group" = "critical-scan-only"
