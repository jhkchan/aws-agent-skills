# Eval prompt: custom-resource-lambda-timeout

Diagnose the CloudFormation stack rollback failure for the following
stack. Walk the rollback-focused diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-infrastructure` is stuck in `UPDATE_ROLLBACK_FAILED`
after a failed update. The custom resource `AppConfigCustomResource`
failed to roll back because the provider Lambda timed out without
sending a response to the CloudFormation signal URL.

```text
StackName: prod-infrastructure
StackStatus: UPDATE_ROLLBACK_FAILED
StackId: arn:aws:cloudformation:us-east-1:111111111111:stack/prod-infrastructure/abc-123

Failed resource:
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
  Last log before timeout:
    "2025-08-05T14:23:11.012Z Processing Delete request for
    AppConfig environment=prod"
    "Task timed out after 3.00 seconds"

Stack policy: (none — no stack policy set)
Drift: (none detected)
Nested stacks: (none)
```

The custom resource's provider Lambda has a 3-second timeout. During
rollback, the Delete request takes longer than 3 seconds and the Lambda
times out before calling `cfnresponse.send`. CloudFormation waits the
full hour, then fails. Identify the layer and recommend the fix.
