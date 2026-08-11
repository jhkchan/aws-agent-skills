# End-to-end usage scenario: cloudformation-drift-troubleshooter

A walkthrough showing the skill diagnosing a CloudFormation
`StackDriftStatus: DRIFTED` caused by an out-of-band modification of
an S3 bucket policy on `LogsBucket`. This exercises Step 0 (signal
capture), Step 1 (refresh detection), Step 2 (per-resource
classification), Step 3 (forensic walk via CloudTrail + Config),
Step 4 (immutable-property probe via ChangeSet), Step 5
(resolution choice — RESET_TO_DRIFT), and Step 8 (prevention).

## Input (user prompt)

> Our `logging-stack` in `us-east-1` shows `StackDriftStatus:
> DRIFTED`. The `LogsBucket` resource has `MODIFIED` drift on its
> `BucketPolicy` Principal — it now points at
> `arn:aws:iam::111122223333:root` instead of
> `logging.us-east-1.amazonaws.com`. CloudTrail shows a
> `PutBucketPolicy` by `dev-alice` on 2026-08-04 adding the
> cross-account grant. The grant is intentional — the dev account
> needs to write logs. We want to clear the drift without breaking
> the grant.

## Skill output

```text
INCIDENT: logging-stack in us-east-1 — StackDriftStatus DRIFTED, 1
drifted resource (LogsBucket)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: MODIFIED on LogsBucket (logging-stack-logsbucket-abc) —
the bucket policy was edited out-of-band on 2026-08-04 by
dev-alice adding a cross-account PutObject grant from account
111122223333, diverging from the template policy
EVIDENCE:
  - describe-stacks: StackStatus CREATE_COMPLETE, StackDriftStatus
    DRIFTED, LastDriftDetectionDateTime 2026-08-05T09:14:22Z
  - describe-stack-resource-drifts: LogsBucket
    ResourceDriftStatus MODIFIED with 1 PropertyDifference on
    /BucketPolicy/Document/Statement/0/Principal from
    {"Service":"logging.us-east-1.amazonaws.com"} to
    {"AWS":"arn:aws:iam::111122223333:root"}
  - CloudTrail: PutBucketPolicy on s3.amazonaws.com at
    2026-08-04T22:11:48Z by
    arn:aws:iam::111122223333:user/dev-alice from source IP 10.42.1.5
  - describe-change-set (drift-impact-probe): LogsBucket Action
    Modify, Replacement False, Scope [Properties] — the policy drift
    does NOT require Replacement
ROOT_CAUSE_CATALOG: #1 (out-of-band modification of CFN-managed resource)
RESOLUTION: RESET_TO_DRIFT
REMEDIATION:
  1. The change appears intentional (the cross-account grant is a
     legitimate logging use case). Accept the drift by updating the
     template to match the actual policy, then create and execute a
     ChangeSet:
     aws cloudformation create-change-set \
       --stack-name logging-stack \
       --change-set-name accept-bucket-policy-drift \
       --change-set-type UPDATE \
       --template-body file://template-with-updated-policy.yaml \
       --capabilities CAPABILITY_IAM
     aws cloudformation describe-change-set \
       --stack-name logging-stack \
       --change-set-name accept-bucket-policy-drift
     Confirm LogsBucket Action Modify, Replacement False. Then:
     aws cloudformation execute-change-set \
       --stack-name logging-stack --change-set-name accept-bucket-policy-drift
  2. Verify drift is resolved:
     DETECTION_ID=$(aws cloudformation detect-stack-drift \
       --stack-name logging-stack --query 'StackDriftDetectionId' --output text)
     aws cloudformation describe-stack-drift-detection-status \
       --stack-drift-detection-id $DETECTION_ID
     Expect StackDriftStatus IN_SYNC after DetectionStatus DETECTION_COMPLETE.
  3. Prevent recurrence — attach a deny policy on
     s3:PutBucketPolicy scoped to this bucket, conditioned on
     aws:CalledViaFirst != cloudformation.amazonaws.com, so future
     edits are made only through the stack.
```

## What the skill caught that a generic assistant misses

1. **Mutable vs immutable property distinction.** A generic
   assistant recommends `update-stack` without probing whether the
   drifted property triggers Replacement. The skill creates a
   `drift-impact-probe` ChangeSet first and confirms
   `Replacement: False` before recommending the update.
2. **Forensic walk via CloudTrail.** A generic assistant suggests
   "checking CloudTrail" but does not run the lookup. The skill
   names the actor, timestamp, and source IP — confirming the
   change is intentional vs malicious.
3. **Resolution choice rationale.** A generic assistant says "either
   accept or revert." The skill picks `RESET_TO_DRIFT` based on the
   intent signal (the grant is legitimate) and the property
   mutability (BucketPolicy is mutable, no Replacement risk).
4. **Prevention step.** A generic assistant stops at remediation.
   The skill adds the `aws:CalledViaFirst` deny policy as a
   recurrence-prevention mechanism.
5. **Re-verification.** A generic assistant does not re-run drift
   detection. The skill mandates `detect-stack-drift` +
   `describe-stack-drift-detection-status` to confirm `IN_SYNC`.

## Slash-command invocation

```
/aws:troubleshoot-cloudformation-drift
```

Or via the orchestrator:

```
/aws:pipeline
You: "logging-stack DRIFTED, LogsBucket bucket policy modified"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
cloudformation-drift-troubleshooter]` and hands off to this skill
for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has credentials for the account:

```bash
# Refresh drift detection.
DETECTION_ID=$(aws cloudformation detect-stack-drift \
  --stack-name logging-stack --query 'StackDriftDetectionId' --output text)
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DETECTION_ID

# Read the per-resource drift.
aws cloudformation describe-stack-resource-drifts --stack-name logging-stack \
  --query 'StackResourceDrifts[?ResourceDriftStatus!=`IN_SYNC`].{logical:LogicalResourceId,physical:PhysicalResourceId,status:ResourceDriftStatus,diffs:PropertyDifferences}' \
  --output table

# Forensic walk via CloudTrail.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=logging-stack-logsbucket-abc \
  --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-05T00:00:00Z \
  --query 'Events[?EventName==`PutBucketPolicy`].{event:EventName,time:EventTime,user:Username,ip:CloudTrailEvent}' \
  --output table

# Probe the update impact.
aws cloudformation create-change-set --stack-name logging-stack \
  --change-set-name drift-impact-probe --change-set-type UPDATE \
  --template-body file://current-template.yaml --capabilities CAPABILITY_IAM
aws cloudformation describe-change-set --stack-name logging-stack \
  --change-set-name drift-impact-probe \
  --query 'Changes[?ResourceChange.LogicalResourceId==`LogsBucket`].ResourceChange.{action:Action,replacement:Replacement,scope:Scope}'
aws cloudformation delete-change-set --stack-name logging-stack \
  --change-set-name drift-impact-probe
```

If `Replacement: False` and the change is intentional, proceed with
the `RESET_TO_DRIFT` flow. If `Replacement: True`, escalate to
`REVERT_TO_TEMPLATE` before any stack update.

## Related scenarios

The same skill handles:

- **`DELETED` drift on a Lambda function** — recreate via stack
  update, or remove from template if intentionally gone.
- **`ADDITION` drift surfaced via Config** — `import-resources` to
  bring under stack management without recreation.
- **`MODIFIED` drift on an immutable property** — `REVERT_TO_TEMPLATE`
  first to avoid Replacement; only `RESET_TO_DRIFT` if Replacement
  is acceptable.
- **Drift on nested stacks** — drill into the child via its ARN;
  the parent's `AWS::CloudFormation::Stack` resource carries the
  child's aggregate status.
- **CDK drift** — use `cdk drift` for construct-level overview;
  cross-reference CloudFormation for resource-level detail.
