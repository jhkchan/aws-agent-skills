---
name: troubleshoot-iam-permission
description: >-
  Slash command for the iam-permission-troubleshooter skill. Diagnoses
  AWS IAM AccessDenied, ExplicitDeny, Client.UnauthorizedOperation, and
  sts:AssumeRole NotAuthorized errors via the six-layer policy evaluation
  decision tree (SCP, resource-based, identity-based, boundary, session,
  VPC endpoint). Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with
  the failing layer and statement.
skill: iam-permission-troubleshooter
family: Security
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
---

# /aws:troubleshoot-iam-permission

Invoke the `iam-permission-troubleshooter` skill to diagnose an AWS IAM
permission failure.

## When to use

- An AWS API call returns `AccessDenied` or `Client.UnauthorizedOperation`.
- `sts:AssumeRole` fails with `NotAuthorized to perform sts:AssumeRole`.
- A Lambda / EC2 / ECS task cannot reach a cross-account resource.
- A new SCP or permissions boundary silently broke a workload.
- `iam simulate-principal-policy` returns an unexpected implicit deny.

## Invocation

```
/aws:troubleshoot-iam-permission <description of the AccessDenied scenario>
```

The skill will:

1. Identify the error type (implicit AccessDenied, explicit Deny, EC2
   Client.UnauthorizedOperation, sts:AssumeRole NotAuthorized,
   cross-account resource access).
2. Request the four mandatory context values: principal ARN, exact
   action, resource ARN, request context (region / source IP / source
   VPCE).
3. Walk the six-layer evaluation order: Organisation SCP → resource-based
   → identity-based → permissions boundary → session policy → VPC
   endpoint.
4. Map the failure to the common root-cause catalog (8 patterns covering
   ~90% of incidents).
5. Verify the proposed fix with `aws iam simulate-principal-policy`
   before applying.
6. Emit the standard VERDICT block.

## Output shape

```text
INCIDENT: <principal> → <action> on <resource>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <layer name> — <statement Sid or missing permission> —
<implicit or explicit deny>
EVIDENCE:
  - <layer>: <Allowed | Denied | Not evaluated> — <evidence line>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific policy edit + verification command>
```

## Pre-flight

The skill requires the CloudTrail event OR a policy simulator result to
distinguish implicit from explicit deny. If neither is available, the
skill emits `NEED_MORE_INFO` with the list of required inputs.

## References

- Skill: `skills/iam-permission-troubleshooter/SKILL.md`
- Reference: `skills/iam-permission-troubleshooter/references/policy-evaluation-logic.md`
- Reference: `skills/iam-permission-troubleshooter/references/common-gotchas.md`
- AWS docs: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
