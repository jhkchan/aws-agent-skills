# Eval prompt: org-trail-consolidation

Optimise the following CloudTrail configuration for cost. Walk the
trail-consolidation decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

TrailName: aws-organizational-trail-primary
IsOrganizationTrail: true
IsMultiRegionTrail: true
IncludeManagementEvents: true
Status: RUNNING

Organization:
  ManagementAccount: 111111111111
  MemberAccounts: 12

Trail inventory (organization):
  - aws-organizational-trail-primary (org trail, RUNNING)
  - member-trail-acct-2 (member trail in acct 222222222222)
  - member-trail-acct-3 (member trail in acct 333333333333)
  - member-trail-acct-4 (member trail in acct 444444444444)
  - member-trail-acct-5 (member trail in acct 555555555555)
  - member-trail-acct-6 (member trail in acct 666666666666)
  - member-trail-acct-7 (member trail in acct 777777777777)
  - member-trail-acct-8 (member trail in acct 888888888888)
  - member-trail-acct-9 (member trail in acct 999999999999)
  - member-trail-acct-10 (member trail in acct 101010101010)
  - member-trail-acct-11 (member trail in acct 111111111112)
  - member-trail-acct-12 (member trail in acct 121212121212)
  - member-trail-acct-13 (member trail in acct 131313131313)

Metrics (last 90 days):
  - Org trail log files/month: 1,400,000
  - Member trail log files/month (each): 116,667
  - Total duplicate log files/month: 1,400,000 (org-mgmt events)
  - KMS keys: 13 (one per trail)
  - SNS topics: 13 (one per trail)
  - S3 storage for duplicate logs: 200 GB

Region: us-east-1
