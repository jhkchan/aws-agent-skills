# Eval prompt: membership-gap-invited-not-active

Audit the following AWS Clean Rooms collaboration for membership,
privacy-budget, analysis-template, and configured-audience posture.
Emit the standard VERDICT block (COLLABORATION, VERDICT, REASON,
FINDINGS, REMEDIATION).

Collaboration id: arn:aws:cleanrooms:us-east-1:111111111111:collaboration/membership-gap-invited-not-active
Collaboration metadata:
  name: membership-gap-invited-not-active
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
- accountId: "333333333333"
  status: INVITED
  displayName: 333-analyst
  abilities: [CAN_QUERY]

Differential privacy config:
  enabled: true
  epsilonBudgetPerMember: 10.0

Most recent protected query:
  status: SUCCEEDED
  additionalAnalyses: 0.5
