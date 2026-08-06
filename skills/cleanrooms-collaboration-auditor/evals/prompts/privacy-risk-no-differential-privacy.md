# Eval prompt: privacy-risk-no-differential-privacy

Audit the following AWS Clean Rooms collaboration for membership,
privacy-budget, analysis-template, and configured-audience posture.
Emit the standard VERDICT block (COLLABORATION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Collaboration id: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/privacy-risk-no-differential-privacy
Collaboration metadata:
  name: privacy-risk-no-differential-privacy
  status: ACTIVE
  creatorDisplayName: 111-creator
  creatorMemberAbilities: [CAN_QUERY, CAN_CONFIGURE_COLLABORATION]
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
  enabled: false

Configured table cr-events:
  allowedColumns: [user_id, event_type, ts]
  analysisRuleType: AGGREGATION
  aggregateConstraints: []

Most recent protected query:
  status: SUCCEEDED
  additionalAnalyses: 0
