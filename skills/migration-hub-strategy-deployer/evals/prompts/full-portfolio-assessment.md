# Eval prompt: full-portfolio-assessment

Design a full Migration Hub Strategy assessment for the following
portfolio. Emit the standard ASSESSMENT block (DISCOVERY_METHOD,
COLLECTOR_PLAN, ASSESSMENT_SCHEDULE, STRATEGY_GROUPS, ANTI_PATTERNS,
TCO, RIGHT_SIZING, WAVE_PLAN, MGN_HANDOFF, DMS_HANDOFF, VERDICT, GAP,
TEMPLATE).

Design reference: full-portfolio-assessment
Account: 111111111111
Home region: us-east-1
vCenter: vcenter.example.com (reachable on 443)

Portfolio: 120 servers across 8 applications.
Discovery: agent-based on 120 critical hosts + agentless Collector on vCenter.
Collection window: 14 days.
Anti-patterns expected: Windows Server 2012 R2 EOL (srv-042), Oracle 11g (srv-078).
MGN service role: configured. DMS replication instance: provisioned.
S3 report bucket: s3://migration-reports-111111111111/portfolio-q3/
