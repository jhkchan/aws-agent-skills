# Eval prompt: auto-tag-on-create

Design an EventBridge + Lambda auto-tagging pipeline that stamps
tags on resource creation. Emit the standard GOVERNANCE block
(SCOPE, STRATEGY, POLICY, AUTOMATION, COMPLIANCE, VERDICT, GAP,
TEMPLATE).

Design reference: auto-tag-on-create
Account: 111111111111
Region: us-east-1

Requirement: auto-tag resources at creation.
On EC2 RunInstances, S3 CreateBucket, Lambda CreateFunction20150331:
derive and stamp the following tags:
- Owner: from userIdentity ARN (extract the user/role name)
- CreatorARN: full userIdentity ARN
- Environment: from account-id-to-environment map
- CreatedVia: "auto-tagger"
- CreatedAt: eventTime

Include the EventBridge rule pattern, the Lambda handler dispatch
logic, the Lambda execution role permissions, and a DLQ for failed
invocations.
