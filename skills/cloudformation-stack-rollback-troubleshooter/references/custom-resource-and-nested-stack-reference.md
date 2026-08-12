# Custom Resource and Nested Stack Rollback Reference

Supplementary reference for the CloudFormation Stack Rollback
Troubleshooter skill. Loaded on-demand when a diagnostic needs custom
resource lifecycle semantics, `cfnresponse` protocol details, nested
stack rollback ordering, or `continue-update-rollback --resources-to-skip`
guidance.

## Custom resource lifecycle and the CFN signal URL

A custom resource (`Custom::*` or `AWS::CloudFormation::CustomResource`)
delegates management to a provider — typically a Lambda function
identified by the `ServiceToken` property. The provider must send a
SUCCESS or FAILED response to a pre-signed S3 URL that CloudFormation
provides in the request body.

### Request flow

```
CloudFormation → Provider Lambda → (process) → Response to S3 URL
                                              ↑
                                              cfnresponse.send(event, context, status, data, physicalResourceId)
```

### Request types and when they fire

| RequestType | When it fires | During rollback? |
|---|---|---|
| `Create` | Initial stack creation or new resource | No (rollback doesn't re-create) |
| `Update` | Resource properties change on stack update | No (rollback sends Delete) |
| `Delete` | Resource is removed from the template OR rollback | Yes — rollback sends Delete with old properties |
| `Update` (rollback) | Rollback of a failed update | Rare; only if the resource was Modified during the failed update |

### The 1-hour CloudFormation timeout

CloudFormation waits up to **1 hour** (3600 seconds) for a custom
resource response. This is separate from the Lambda function's own
`Timeout` (default 3 seconds, max 900 seconds). If the Lambda times out
at 3 seconds but doesn't send a response, CloudFormation doesn't know
the Lambda failed — it waits the full hour.

### Common failure patterns during rollback

| Pattern | Root cause | Fix |
|---|---|---|
| Lambda timed out (3s default) | `Timeout` too low for the Delete operation | Raise Lambda `Timeout` to 30-60s |
| Lambda didn't call `cfnresponse.send` | Missing error handling; the handler caught an exception and exited without sending FAILED | Wrap handler in try/finally; always call `cfnresponse.send` |
| Wrong response URL | Provider used a hardcoded or stale S3 URL instead of `event.ResponseURL` | Use `event.ResponseURL` from the request |
| Provider Lambda deleted | The `ServiceToken` Lambda was removed | Recreate the Lambda or update the ServiceToken |
| Provider doesn't handle `Delete` | Handler only processes `Create`; `Delete` falls through without responding | Add explicit `RequestType: Delete` handling |
| PhysicalResourceId mismatch on rollback | Provider returns a different PhysicalResourceId on Delete than it returned on Create | Always echo back the same PhysicalResourceId from the original Create |

### cfnresponse snippet (Node.js)

```javascript
const response = require('cfn-response');

exports.handler = async (event, context) => {
  try {
    if (event.RequestType === 'Delete') {
      // Handle deletion — clean up the physical resource
      await cleanupResource(event.PhysicalResourceId);
    } else if (event.RequestType === 'Create') {
      // Handle creation
      const id = await createResource(event.ResourceProperties);
      response.send(event, context, response.SUCCESS, { Id: id }, id);
      return;
    } else if (event.RequestType === 'Update') {
      // Handle update
      await updateResource(event.PhysicalResourceId, event.ResourceProperties);
    }
    response.send(event, context, response.SUCCESS, {});
  } catch (err) {
    console.error('Provider error:', err);
    response.send(event, context, response.FAILED, { Error: err.message });
  }
};
```

**Critical:** the `catch` block ensures `cfnresponse.send` is called
with FAILED even on errors. Without it, the Lambda exits without
responding and CloudFormation waits the full hour.

### Python cfnresponse alternative

```python
import cfnresponse
import json

def handler(event, context):
    try:
        request_type = event['RequestType']
        if request_type == 'Delete':
            cleanup(event['PhysicalResourceId'])
        elif request_type == 'Create':
            resource_id = create(event['ResourceProperties'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS,
                             {'Id': resource_id}, resource_id)
            return
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        print(f"Provider error: {e}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
```

### Bypassing a stuck custom resource

When the provider Lambda can't be fixed quickly, use
`continue-update-rollback --resources-to-skip`:

```bash
aws cloudformation continue-update-rollback \
  --stack-name <name> \
  --resources-to-skip <custom-resource-logical-id> \
  --profile <p>
```

CloudFormation marks the resource as successfully rolled back without
sending a request to the provider. The resource becomes **orphaned** —
it still exists physically but CloudFormation no longer tracks it in
the stack. Future stack updates will not manage it.

## Nested stack rollback semantics

A nested stack is an `AWS::CloudFormation::Stack` resource within a
parent template. Each nested stack is an independent CloudFormation
stack with its own status, events, and rollback behaviour.

### Rollback ordering

```
Parent stack update fails
  → Parent begins UPDATE_ROLLBACK_IN_PROGRESS
    → For each nested stack resource:
      → If child was Modified: rollback the child
        → Child enters UPDATE_ROLLBACK_IN_PROGRESS
        → If child rollback succeeds: child = UPDATE_ROLLBACK_COMPLETE
        → If child rollback fails: child = UPDATE_ROLLBACK_FAILED
      → If child rollback failed: parent rollback also fails
        → Parent = UPDATE_ROLLBACK_FAILED
```

### Fixing a nested stack cascade

Always fix the **deepest child first**, then work upward:

1. Identify the deepest child in `UPDATE_ROLLBACK_FAILED`.
2. Diagnose that child's blocking resource (recurse through the
   diagnostic tree for the child).
3. Run `continue-update-rollback` on the child (with `--resources-to-skip`
   if needed).
4. Wait for the child to reach `UPDATE_ROLLBACK_COMPLETE`.
5. Run `continue-update-rollback` on the parent.

### Common mistakes

| Mistake | Consequence |
|---|---|
| Running CUR on the parent before fixing the child | Parent retries child rollback; child is still stuck; parent fails again |
| Deleting the child stack manually | Parent can't find the child; parent rollback fails differently |
| Deleting the parent stack to "start over" | All resources (including unrelated child resources) are destroyed |

### Identifying the child stack ARN

```bash
aws cloudformation describe-stack-resource \
  --stack-name <parent> \
  --logical-resource-id <NestedStackLogicalId> \
  --output json | jq '.StackResourceDetail.PhysicalResourceId'
```

The `PhysicalResourceId` is the child stack's ARN. Use it with
`describe-stacks` and `describe-stack-events` to diagnose the child.

## continue-update-rollback in detail

### Command syntax

```bash
aws cloudformation continue-update-rollback \
  --stack-name <name> \
  [--resources-to-skip <logical-id-1> <logical-id-2> ...] \
  [--client-request-token <token>] \
  --profile <p>
```

### What it does

1. Resumes the rollback from the point of failure.
2. For resources NOT in `--resources-to-skip`: retries the rollback
   operation (Delete or Update).
3. For resources IN `--resources-to-skip`: marks them as
   `UPDATE_COMPLETE` without touching them. The physical resource
   remains in whatever state it's currently in.

### When to use --resources-to-skip

| Scenario | Skip the resource? |
|---|---|
| Custom resource provider Lambda can't be fixed quickly | Yes — bypass the stuck custom resource |
| IAM role can't be deleted (active sessions) | Yes — detach role manually first, then skip |
| RDS instance has data you can't lose | Yes — manage manually after rollback |
| Security group drift | No — fix the drift and retry normally |
| Nested child stack | No — fix the child's resources, then retry the parent |

### Monitoring the rollback

```bash
# Watch the stack status
aws cloudformation describe-stacks \
  --stack-name <name> --output json | \
  jq '.Stacks[0].StackStatus'

# Watch the events
aws cloudformation describe-stack-events \
  --stack-name <name> --output json | \
  jq '.StackEvents[0:10] | .[] | \
      {Timestamp, LogicalResourceId, ResourceType, ResourceStatus}'
```

Wait for `UPDATE_ROLLBACK_COMPLETE`. If the status returns to
`UPDATE_ROLLBACK_FAILED`, another resource is blocking — repeat the
diagnosis for the next blocking resource.

## DeletionPolicy and UpdateReplacePolicy

### DeletionPolicy values

| Value | Behaviour during stack delete | Behaviour during rollback |
|---|---|---|
| `Delete` (default) | CloudFormation deletes the resource | CloudFormation deletes resources created during the failed update |
| `Retain` | CloudFormation keeps the resource (orphaned) | CloudFormation keeps resources; rollback "succeeds" for retained resources without modifying them |
| `Snapshot` (RDS, Aurora, Redshift, Neptune, DocDB only) | CloudFormation creates a final snapshot before deleting | Same as Delete but with a snapshot |

### UpdateReplacePolicy values

Controls what happens to the **old** resource when a property with
`Replacement: True` changes during an update.

| Value | Old resource |
|---|---|
| `Delete` (default) | Deleted after the new resource is created |
| `Retain` | Kept (orphaned) after the new resource is created |
| `Snapshot` | A snapshot is created before deletion |

### Common pitfalls

- `DeletionPolicy: Retain` on a resource that changes during update:
  the old version is retained, but CloudFormation may fail to
  reconcile the retained resource on rollback.
- `DeletionPolicy: Snapshot` on RDS: if the snapshot name conflicts
  with an existing snapshot, the deletion fails and the rollback
  blocks.
- Missing `UpdateReplacePolicy`: defaults to `Delete`, which removes
  the old resource — if it's in use, the rollback fails.
