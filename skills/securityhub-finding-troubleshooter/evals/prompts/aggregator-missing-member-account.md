# Eval prompt: aggregator-missing-member-account

Diagnose the cross-account aggregation issue below. Walk the
standard-driven decision tree and emit the standard diagnostic block
(FINDING, VERDICT, REASON, LAYER, SEVERITY, STANDARD, EVIDENCE,
SUPPRESSION, REMEDIATION). The FINDING line must reference the
test-case id `aggregator-missing-member-account`.

Symptom: SOC for the aggregator account 111111111111 (us-east-1)
cannot see findings from member account 222222222222 even though both
accounts are in the same AWS Organization. Member account administrator
confirmed High-severity findings exist locally but the aggregator view
is empty.

```text
aws securityhub get-finding-aggregator (from account 111111111111):
  FindingAggregatorArn: arn:aws:securityhub:us-east-1:111111111111:finding-aggregator/default
  RegionLinkingMode: ALL_REGIONS

aws securityhub list-members (from account 111111111111):
  Member accounts: [333333333333, 444444444444]
  NOTE: 222222222222 is NOT listed.

aws securityhub get-administrator-account (from 222222222222):
  AdministratorAccount: (empty — no administrator set)
  (the member was never successfully associated)

aws organizations describe-organization:
  OrganizationId: o-abc123def
  ManagementAccount: 555555555555
  Both 111111111111 (aggregator) and 222222222222 (target member)
  are member accounts in the org.

aws securityhub list-organization-admin-accounts:
  AdminAccountId: 111111111111 (the aggregator IS delegated)

Member account 222222222222 operator: "We received an invitation
last quarter but it expired before we could accept. Can we re-invite?"

Note: The operator in 111111111111 cannot assume a role in
222222222222 to verify the local Security Hub state directly.
They can only see the aggregator-side view.
```

Emit the standard diagnostic block.
