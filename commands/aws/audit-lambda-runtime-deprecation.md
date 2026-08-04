---
description: Audit a Lambda function for deprecated/EOL runtimes, over-permissioned execution roles, public function URL exposure, and observability config gaps.
nl_triggers:
  - "audit this Lambda function"
  - "check Lambda runtime"
  - "is my Lambda runtime deprecated"
  - "Lambda runtime EOL"
  - "check Lambda execution role"
  - "Lambda admin role"
  - "is my function URL public"
  - "Lambda AuthType NONE"
  - "missing X-Ray tracing Lambda"
  - "Lambda TracingConfig"
  - "Lambda dead letter queue"
  - "hardening Lambda function"
  - "Lambda runtime deprecation"
  - "nodejs16 Lambda"
  - "python3.9 Lambda"
  - "Lambda security audit"
routes_to: lambda-runtime-deprecation-auditor
---

# /aws:audit-lambda-runtime-deprecation

Activate the `lambda-runtime-deprecation-auditor` skill and audit one or
more Lambda function configurations for runtime deprecation, execution-role
scope, public exposure, and observability gaps.

## What it does

Reads a Lambda function configuration (Runtime, TracingConfig, DeadLetterConfig,
Function URL config) plus execution-role policies and applies the ordered
classification logic:

1. Pre-flight function metadata gate — short-circuit container-image
   functions (PackageType: Image — no runtime to check), custom runtimes
   (provided.al2023 is current), and provided (AL1 — fully EOL).
2. Runtime lifecycle — compare Runtime against the supported-runtime set.
   Deprecated/Phase 1 = time bomb; Blocked/Phase 2 = invocations already
   failing.
3. Function URL / public exposure — AuthType NONE is publicly invocable.
4. Execution role / IAM — admin wildcards, privilege-escalation service
   wildcards, NotAction/NotResource.
5. Observability / config gaps — PassThrough tracing, missing DLQ,
   reserved concurrency 0.
6. Aggregation — worst finding wins (DEPRECATED_RUNTIME > PUBLIC_EXPOSURE
   > OVERPERMISSIVE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per function:

```text
FUNCTION: <function-name>
VERDICT: DEPRECATED_RUNTIME | PUBLIC_EXPOSURE | OVERPERMISSIVE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [DEPRECATED_RUNTIME] <finding description (Step 1)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Lambda function configuration and ask any of:

- "audit this Lambda function"
- "is my Lambda runtime deprecated?"
- "check the execution role for this function"
- "is my function URL publicly accessible?"
- "is X-Ray tracing enabled on this function?"
- "what runtime should I upgrade to?"

A bare function name or ARN + any audit verb ("audit this function",
"check Lambda runtime") also routes here via the orchestrator.

## Inputs

- A Lambda function configuration: Runtime, Handler, TracingConfig,
  DeadLetterConfig, Architectures, PackageType, LastModified.
- Execution-role policies (managed + inline JSON documents).
- Function URL config (AuthType, Cors) if configured.
- For multi-function sweeps: provide all functions; the skill paginates.

## Outputs

- One VERDICT block per function (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: update runtime, restrict URL auth, scope down
  role, enable tracing, add DLQ.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Lambda compute security).
- `/aws:audit-iam-least-privilege` for detailed IAM policy analysis of the
  execution role.
