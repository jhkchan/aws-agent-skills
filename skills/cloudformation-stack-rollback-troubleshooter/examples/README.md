# Example usage: cloudformation-stack-rollback-troubleshooter

A walkthrough showing the skill diagnosing an `UPDATE_ROLLBACK_FAILED`
stack where the blocking resource is a custom resource Lambda that
timed out during rollback — the #1 rollback blocker. The skill
identifies the specific blocking resource, names the root cause, and
recommends the immediate unblock (`continue-update-rollback
--resources-to-skip`) plus the permanent fix (raise Lambda Timeout).

## Input (user prompt)

> Our prod-infrastructure stack is stuck in UPDATE_ROLLBACK_FAILED
> after a failed update. The stack event shows the custom resource
> AppConfigCustomResource failed — something about the provider Lambda
> timing out. We've been trying to figure out why the rollback won't
> complete for over an hour. Please help us unblock.

```text
StackName: prod-infrastructure
StackStatus: UPDATE_ROLLBACK_FAILED
StackId: arn:aws:cloudformation:us-east-1:111111111111:stack/prod-infrastructure/abc-123

Failed resource (from describe-stack-events):
  Timestamp: 2025-08-05T15:23:11.012Z
  LogicalResourceId: AppConfigCustomResource
  ResourceType: Custom::AppConfig
  ResourceStatus: DELETE_FAILED
  ResourceStatusReason: "Custom Resource failed: Provider did not
    respond within 60 minutes. Last known state: Provider Lambda
    function timed out."

Provider Lambda context:
  FunctionName: appconfig-custom-resource-provider
  Timeout: 3
  Runtime: nodejs20.x
  Handler: index.handler
  LastCloudWatchLog:
    "2025-08-05T14:23:11.012Z Processing Delete request for
    AppConfig environment=prod"
    "2025-08-05T14:23:14.013Z Task timed out after 3.00 seconds"

Stack policy: (none — no stack policy set)
Drift: (none detected)
Nested stacks: (none)
```

## Skill output

```text
TARGET: prod-infrastructure
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The stack is in UPDATE_ROLLBACK_FAILED. The blocking resource
  is Custom::AppConfig (LogicalId: AppConfigCustomResource). The provider
  Lambda function (appconfig-custom-resource-provider) timed out at 3s
  (its configured Timeout) while processing a Delete request during
  rollback. CloudFormation waited the full hour, then failed. The
  Lambda's own logs show "Task timed out after 3.00 seconds" with the
  last log line "Processing Delete request for AppConfig" — the
  provider started processing but didn't finish within 3 seconds and
  never called cfnresponse.send.
LAYER: CUSTOM_RESOURCE_TIMEOUT
EVIDENCE:
  - Symptom: stack prod-infrastructure is in UPDATE_ROLLBACK_FAILED.
    describe-stack-events shows AppConfigCustomResource with
    ResourceStatus: DELETE_FAILED and ResourceStatusReason: "Custom
    Resource failed: Provider did not respond within 60 minutes."
  - Probe: aws logs filter-log-events on
    /aws/lambda/appconfig-custom-resource-provider returns "Task timed
    out after 3.00 seconds" at 14:23:14Z. The preceding log line is
    "Processing Delete request for AppConfig environment=prod" — the
    Lambda received the Delete request but didn't finish processing
    within 3 seconds.
  - Probe: aws lambda get-function-configuration returns Timeout: 3
    for appconfig-custom-resource-provider. The Lambda's 3-second
    timeout is far too short for an AppConfig Delete operation that
    involves calling the AppConfig API and waiting for confirmation.
  - Passing: no nested stacks in the template (not a cascade); no IAM
    resources with Replacement: True (not an IAM replacement); no
    drift detected (describe-stack-resource-drifts returns all
    IN_SYNC); no stack policy set (not a policy block).
REMEDIATION:
  1. Immediate unblock: bypass the stuck custom resource with
     ContinueUpdateRollback so the rest of the stack can roll back:
     aws cloudformation continue-update-rollback \
       --stack-name prod-infrastructure \
       --resources-to-skip AppConfigCustomResource \
       --profile <p>
     WARNING: AppConfigCustomResource will be orphaned — it still
     exists physically but CloudFormation will no longer track it.
     Clean it up manually after the rollback.
  2. Fix the provider Lambda: raise its Timeout to 30 seconds and
     ensure it handles RequestType: Delete (and calls cfnresponse.send
     for all request types):
     aws lambda update-function-configuration \
       --function-name appconfig-custom-resource-provider \
       --timeout 30 --profile <p>
  3. Verify the provider Lambda handles Delete by checking the handler
     code. The provider must:
     - Process event.RequestType === 'Delete' (cleanup the AppConfig)
     - Call cfnresponse.send(event, context, 'SUCCESS', {}) or FAILED
     - Handle errors in a try/catch that always calls cfnresponse.send
  4. After fixing the Lambda, import the orphaned custom resource back
     into the stack (if tracking is needed) using
     import-resources-to-stack.
CONFIRM: Before running continue-update-rollback, emit and await:
  "CONFIRM: About to continue-update-rollback on prod-infrastructure,
   skipping AppConfigCustomResource. The custom resource will be
   orphaned (still exists physically but CFN stops tracking it).
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Identified the #1 rollback blocker pattern.** A generic assistant
   sees "stack stuck in UPDATE_ROLLBACK_FAILED" and says "try
   continue-update-rollback." The skill reads the events, identifies
   the custom resource as the blocking resource, and names the pattern:
   the provider Lambda timed out at 3 seconds (its configured Timeout)
   before calling `cfnresponse.send`. This is the most common rollback
   blocker.

2. **Distinguished the Lambda Timeout from the CloudFormation 1-hour
   wait.** A generic assistant might say "the Lambda timed out" without
   explaining why the rollback took an hour. The skill explains that
   the Lambda's 3-second timeout is separate from CloudFormation's
   1-hour wait — CFN doesn't know the Lambda failed; it just sees no
   response.

3. **Recommended --resources-to-skip with an orphan warning.** A
   generic assistant says "skip the resource." The skill warns that the
   resource becomes orphaned (still exists physically, CFN stops
   tracking it, may incur charges) and recommends cleaning it up
   manually afterward.

4. **Named both the immediate unblock and the permanent fix.** The
   skill recommends the immediate unblock (`continue-update-rollback
   --resources-to-skip`) AND the permanent fix (raise Lambda Timeout
   to 30s, ensure the handler processes Delete and calls
   `cfnresponse.send` in all paths). A generic assistant typically
   gives only the immediate workaround.

5. **Ruled out other layers with positive evidence.** The skill
   confirmed no nested stacks (not a cascade), no IAM Replacement
   (not an IAM issue), no drift (all IN_SYNC), and no stack policy
   (not a policy block). This narrows the diagnosis to the custom
   resource with certainty.

## Slash-command invocation

```
/aws:troubleshoot-cloudformation-rollback
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why prod-infrastructure is stuck in UPDATE_ROLLBACK_FAILED"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: cloudformation-stack-rollback-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the stack status and the provider Lambda:

```bash
# Confirm the stack reached UPDATE_ROLLBACK_COMPLETE
aws cloudformation describe-stacks \
  --stack-name prod-infrastructure --profile default \
  --query 'Stacks[0].StackStatus'

# Confirm the provider Lambda has the new Timeout
aws lambda get-function-configuration \
  --function-name appconfig-custom-resource-provider \
  --profile default --query 'Timeout'

# If the operator cleaned up the orphaned custom resource manually,
# verify it no longer exists in the AppConfig service
aws appconfig get-environment \
  --application-id <id> --environment-id <id> \
  --profile default 2>/dev/null || echo "Environment cleaned up"

# Run drift detection to confirm the stack is clean after rollback
aws cloudformation detect-stack-drift \
  --stack-name prod-infrastructure --profile default
```

Then monitor the stack for the next deployment cycle to confirm the
fixed provider Lambda handles Delete correctly (check CloudWatch logs
for "cfnresponse" SUCCESS entries on Delete requests).
