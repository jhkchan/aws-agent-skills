# Eval prompt: cross-account-destination-policy-missing

Diagnose the CloudWatch Logs not-ingesting scenario for the following
cross-account setup. Walk the symptom-driven diagnostic tree and emit
the standard diagnostic block (TARGET, VERDICT, REASON, LAYER,
EVIDENCE, REMEDIATION).

Symptom: source account `222222222222` is configured to send
application logs to a log group in destination account `111111111111`.
No events appear in the destination log group. The source account's
emitter role has `logs:PutLogEvents` in IAM.

```text
Destination LogGroup: /cross-account/cross-account-destination-policy-missing
Destination account: 111111111111
Source account: 222222222222
Source emitter role: arn:aws:iam::222222222222:role/log-emitter

aws iam simulate-principal-policy for
arn:aws:iam::222222222222:role/log-emitter (source side):
  logs:PutLogEvents on
  arn:aws:logs:us-east-1:111111111111:log-group:/cross-account/*:
  ALLOWED

aws logs describe-resource-policies --profile 111111-profile:
  resourcePolicies: []
  (empty — no resource policy on the destination account grants the
  source account access)

aws logs describe-destinations --profile 111111-profile:
  destinations: []
  (no put-destination configured for cross-account delivery)

aws logs describe-log-groups --log-group-name-prefix
/cross-account/cross-account-destination-policy-missing
--profile 111111-profile:
  logGroups: [{
    logGroupName: /cross-account/cross-account-destination-policy-missing,
    storedBytes: 0,
    retentionInDays: 90
  }]
  (log group exists but is empty)

CloudTrail (source account): PutLogEvents calls from the emitter role
return AccessDenied.
```

Cross-account log delivery requires a resource-based policy on the
destination (account 111111111111) granting the source account
(222222222222) `logs:PutLogEvents`. The source account's IAM policy is
necessary but not sufficient. Without the destination-side policy,
PutLogEvents calls return AccessDenied even though the source IAM
simulation shows ALLOWED.
