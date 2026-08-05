# Eval prompt: ok-fully-configured-clean-collaboration

Audit the following AWS Clean Rooms collaboration for membership,
privacy-budget, analysis-template, and configured-audience posture.
Emit the standard VERDICT block (COLLABORATION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Collaboration id: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/ok-fully-configured-clean-collaboration
Collaboration metadata:
  name: ok-fully-configured-clean-collaboration
  status: ACTIVE
  creatorDisplayName: 111-creator
  queryLogStatus: ENABLED
  analyticsEngine: CLEAN_ROOMS_SQL
  configuredAudienceModelArn: arn:aws:cleanroomsml:us-east-1:111111111111:configured-audience-model/cam-456

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
    SELECT event_type, COUNT(DISTINCT user_id) AS uniq
    FROM cr-events
    GROUP BY event_type
  parameters: []

Configured audience model state:
  status: READY
  trainingContainerExecutionStatus: SUCCEEDED
