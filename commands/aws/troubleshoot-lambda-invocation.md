---
description: Diagnose AWS Lambda function invocation failures through an eight-category (timeout, OOM, cold start, AccessDenied, VPC, env var, invocation type, ECR) diagnostic tree — emits ROOT_CAUSE_FOUND with the specific failure layer or ESCALATE.
nl_triggers:
  - "Lambda TaskTimeoutException"
  - "Task timed out Lambda"
  - "Lambda out of memory"
  - "Runtime.ExitError"
  - "Lambda cold start"
  - "init duration Lambda"
  - "Lambda AccessDenied"
  - "execution role denied Lambda"
  - "Lambda cannot reach internet"
  - "Lambda cannot reach S3"
  - "Lambda VPC timeout"
  - "Lambda environment variable KMS"
  - "Lambda decrypt error"
  - "Lambda async retry storm"
  - "EventSourceMapping retry"
  - "Lambda container image pull"
  - "ECR image pull error Lambda"
  - "Lambda provisioned concurrency"
  - "troubleshoot Lambda invocation"
  - "diagnose Lambda function failure"
  - "Lambda function 502"
routes_to: lambda-invocation-troubleshooter
---

# /aws:troubleshoot-lambda-invocation

Activate the `lambda-invocation-troubleshooter` skill and diagnose an
AWS Lambda function invocation failure through the eight-category
diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour, caller
context) plus the function configuration, then walks the symptom-driven
diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — function state and LastUpdateStatus
   (`get-function-configuration`), recent log events (`filter-log-events`
   on `/aws/lambda/<name>`), AWS Health (regional incidents).
   Short-circuits on `Failed` LastUpdateStatus, deprecated runtime, or
   AWS-side Lambda service events.
2. **Symptom entry** — map the error to one of: TaskTimeoutException,
   Runtime.ExitError OOM, cold-start init latency, AccessDenied,
   VPC/network error, environment variable error, invocation-type
   mismatch, container image pull failure.
3. **Layer-specific probes** —
   - Timeout: CloudWatch Duration vs configured Timeout, last log line
     before kill, downstream service metrics (DB throttling, dependency
     5xx), VPC-induced timeout (no NAT route).
   - OOM: CloudWatch MaxMemoryUsed vs MemorySize, payload-size
     correlation, leak detection (Max Memory Used trend).
   - Cold start: InitDuration metric, SnapStart (Java only), provisioned
     concurrency on the invoked alias, image size for container
     functions.
   - Permissions: CloudTrail lookup-events for the exact denied API;
     execution-role identity-based policy; cross-account resource-based
     policy on the function; VPC endpoint policy.
   - VPC: VpcConfig populated, subnet route table (NAT for internet,
     Gateway endpoint for S3/DynamoDB, Interface endpoint for other
     services), SG egress, endpoint policy.
   - Environment: KMSKeyArn (customer-managed vs service-managed);
     execution-role `kms:Decrypt` simulate-principal-policy; alias vs
     $LATEST env var divergence.
   - Invocation type: async retry sequence (immediate, +1m, +2m),
     DeadLetterConfig, DestinationConfig.OnFailure; sync caller timeout
     (API Gateway 29/30s, ALB 60s) vs Lambda Timeout.
   - Container image: PackageType Image, Code.ImageUri,
     ecr describe-images (exists, size), ecr get-repository-policy
     (cross-account), ImageConfig.Command alignment with image entry
     point.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   symptom), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side incident; surface AWS Health event ARN).

Emits a deterministic diagnostic block per target:

```text
TARGET: <function-name with qualifier>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TIMEOUT_CONFIG | TIMEOUT_DOWNSTREAM | MEMORY_CONFIG |
        COLD_START | PERMISSION_EXECUTION_ROLE |
        PERMISSION_RESOURCE_POLICY | VPC_CONNECTIVITY | VPC_ENDPOINT |
        ENV_VAR_KMS | ENV_VAR_MISSING | INVOCATION_ASYNC |
        INVOCATION_SYNC | ECR_IMAGE | ECR_POLICY |
        RUNTIME_UNSUPPORTED | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "Lambda function returns TaskTimeoutException"
- "Runtime.ExitError out of memory on Lambda"
- "Lambda cold start is 4 seconds"
- "Lambda AccessDenied calling S3"
- "Lambda in VPC cannot reach the internet"
- "Lambda KMS decrypt error after key rotation"
- "async Lambda invocation retries forever"
- "API Gateway returns 504 from Lambda"
- "container Lambda ImagePullFailure"

A bare function name + any error verb ("Lambda failing", "function
times out", "invocation error") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern, caller (API Gateway / EventBridge / S3 /
  direct Invoke).
- Function configuration: name, qualifier (alias or version), runtime,
  timeout, memory, handler, VpcConfig, Environment, KMSKeyArn,
  PackageType, ImageConfig, LastUpdateStatus.
- For live-account diagnosis: caller context — invocation type (sync
  RequestResponse vs async Event), source ARN, region. The skill uses
  `get-function-configuration`, `filter-log-events`, `get-policy`,
  `get-event-source-mapping`, `cloudtrail lookup-events`,
  `iam simulate-principal-policy`, `ec2 describe-route-tables` /
  `describe-security-groups` / `describe-vpc-endpoints`, `kms
  describe-key`, `ecr describe-images` / `get-repository-policy`.

## Outputs

- One diagnostic block per target function/qualifier.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: timeout/memory raise, role policy edit,
  resource-based policy add, VPC config change, env var add, DLQ /
  destination config, image rebuild, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Lambda invocation failures).
- `/aws:audit-lambda-function` for configuration posture audits on
  the same function (security exposure, runtime deprecation, logging
  coverage).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  Lambda execution role is denied by an SCP, permissions boundary, or
  resource-based policy on the target service.
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when the
  Lambda function cannot reach a destination because of routing, NACL,
  or peering issues.
