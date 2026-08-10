# Eval prompt: abac-policy-design

Design an ABAC IAM policy for team-scoped access to S3 and EC2.
Emit the standard GOVERNANCE block (SCOPE, STRATEGY, POLICY,
AUTOMATION, COMPLIANCE, VERDICT, GAP, TEMPLATE).

Design reference: abac-policy-design
Account: 111111111111
Region: us-east-1

Requirement: team-scoped access via ABAC.
- IAM principals (users and roles) are tagged with Team.
- S3 buckets and EC2 instances are tagged with Team.
- IAM policy must allow read/list access only when
  aws:ResourceTag/Team matches aws:PrincipalTag/Team.
- On resource creation (CreateBucket, RunInstances), require
  aws:RequestTag/Team to match the principal's Team.

Include the IAM policy JSON, the prerequisites checklist, and the
case-sensitivity warning relating to the tag policy's
case_sensitive setting.
