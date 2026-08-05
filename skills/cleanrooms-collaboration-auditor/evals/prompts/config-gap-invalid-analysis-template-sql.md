# Eval prompt: config-gap-invalid-analysis-template-sql

Audit the following AWS Clean Rooms collaboration for membership,
privacy-budget, analysis-template, and configured-audience posture.
Emit the standard VERDICT block (COLLABORATION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Collaboration id: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/config-gap-invalid-analysis-template-sql
Collaboration metadata:
  name: config-gap-invalid-analysis-template-sql
  status: ACTIVE
  creatorDisplayName: 111-creator
  queryLogStatus: ENABLED
  analyticsEngine: CLEAN_ROOMS_SQL

Members (list-members):
- accountId: "111111111111"
  status: ACTIVE
  displayName: 111-creator
  abilities: [CAN_QUERY, CAN_CONFIGURE_COLLABORATION]
- accountId: "222222222222"
  status: ACTIVE
  displayName: 222-marketing
  abilities: [CAN_QUERY]

Differential privacy config:
  enabled: true
  epsilonBudgetPerMember: 10.0

Per-member epsilon spend:
- accountId: "111111111111"
  epsilonSpent: 1.2
- accountId: "222222222222"
  epsilonSpent: 1.5

Configured tables:
- id: cr-events
  allowedColumns: [user_id, event_type, ts]
  analysisRuleType: AGGREGATION
  aggregateConstraints: [{column: user_id, min: 10}]

Analysis template tmpl-events-summary (owned by 111111111111):
  body: |
    SELECT region, COUNT(DISTINCT user_id) AS uniq
    FROM cr_legacy_events
    GROUP BY region
  parameters: []
