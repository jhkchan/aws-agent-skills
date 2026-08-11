---
name: lambda-alias-deployer
description: >-
  Provisions Lambda aliases with production defaults: alias creation
  pointing to a specific published version, traffic shifting
  (weighted aliases for canary/linear deployments), API Gateway
  stage integration (alias as stage trigger), CloudWatch alarm per
  alias, provisioned concurrency on alias, Lambda SnapStart
  integration. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating a Lambda alias, shifting traffic
  between versions, configuring canary deployment, setting up API
  Gateway stage with alias, adding provisioned concurrency to an
  alias, or enabling SnapStart. Triggers: create lambda alias,
  weighted alias, traffic shift lambda, canary deployment lambda,
  provisioned concurrency alias, lambda snapstart alias, API
  gateway stage alias, lambda version alias.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with lambda,
  apigateway, cloudwatch, and iam access. Works with Terraform
  aws_lambda_alias / aws_lambda_provisioned_concurrency_config
  resources and CloudFormation AWS::Lambda::Alias templates.
keywords:
  - aws
  - lambda
  - alias
  - cloudops
  - deploy
  - provisioning
  - traffic shifting
  - weighted alias
  - canary deployment
  - provisioned concurrency
  - snapstart
  - api gateway
  - cloudwatch alarm
  - lambda version
  - stage integration
tags:
  - aws
  - lambda
  - alias
  - cloudops
  - deploy
  - compute
  - provisioning
  - traffic-shifting
  - canary
  - provisioned-concurrency
  - snapstart
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - lambda
    - alias
    - cloudops
    - deploy
    - compute
    - provisioning
    - traffic-shifting
    - canary
    - provisioned-concurrency
    - snapstart
  dependencies:
    - aws-orchestrator
  keywords:
    - create lambda alias
    - weighted alias traffic
    - canary deployment lambda
    - provisioned concurrency alias
    - lambda snapstart alias
    - api gateway stage alias
    - lambda version alias
    - cloudwatch alarm per alias
    - traffic shift lambda
  when_to_use: >-
    Invoke when the user wants to create a Lambda alias pointing to
    a specific published version, configure traffic shifting between
    versions (weighted aliases for canary or linear deployment), set
    up API Gateway stage integration with a Lambda alias, create
    CloudWatch alarms scoped to a specific alias, configure
    provisioned concurrency on an alias, or enable Lambda SnapStart
    with alias-based routing. Do NOT invoke for Lambda function
    creation (use lambda function deployers), for Lambda layer
    management, for EventBridge rule configuration, or for auditing
    existing Lambda alias configurations.
---

# Lambda Alias Deployer

An AWS CloudOps agent skill that provisions Lambda aliases with
correct defaults. The skill walks the operator through published
version requirements, alias creation, traffic shifting, API Gateway
stage integration, CloudWatch alarms per alias, provisioned
concurrency, and SnapStart. It captures deployment and traffic
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Lambda alias, weighted alias, traffic shift Lambda, canary
deployment Lambda, provisioned concurrency alias, Lambda SnapStart
alias, API Gateway stage alias, Lambda version alias, CloudWatch
alarm per alias.

## STRICT output contract

When this skill is invoked with a Lambda-alias-provisioning request
(alias name, version, traffic weights, API Gateway integration,
provisioned concurrency, SnapStart, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined
in the "Output format" section using the literal all-caps labels
`LAMBDA_ALIAS:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of
the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Published version requirement | Version dependency |
| Step 2 — Alias creation | Basic alias setup |
| Step 3 — Traffic shifting (weighted aliases) | Canary/linear deployment |
| Step 4 — API Gateway stage integration | API Gateway routing |
| Step 5 — CloudWatch alarm per alias | Monitoring |
| Step 6 — Provisioned concurrency on alias | Cold-start elimination |
| Step 7 — Lambda SnapStart | JVM/Python fast startup |
| Step 8 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/traffic-shifting-and-concurrency.md | Weighted alias detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** A Lambda alias is a named pointer to a
specific published version of a function. It is the deployment
target for API Gateway, EventBridge, and other triggers. Traffic
shifting between versions uses weighted aliases, not in-place
updates. Provisioned concurrency and SnapStart are configured per
alias.

Three misconceptions dominate Lambda alias misdesign at provisioning
time:

- **"I can point an alias to $LATEST."** You should not. `$LATEST`
  is a mutable, versionless reference that changes on every update.
  Aliases should point to a PUBLISHED version (immutable snapshot).
  Pointing an alias to `$LATEST` defeats the purpose of version
  control: the alias target changes silently when the function is
  updated, bypassing the traffic-shift safety net.

- **"Traffic shifting means updating the function code."** It does
  not. Traffic shifting changes the WEIGHT on the alias to split
  traffic between two published versions. The function code is
  untouched. This is the foundation of canary and linear
  deployments: the new version is published first, then the alias
  weight gradually shifts from old to new.

- **"Provisioned concurrency goes on the function."** It can, but
  the best practice is to put it on the ALIAS, not the function or
  the version. Alias-level provisioned concurrency stays stable as
  you shift traffic: the provisioned capacity follows the alias,
  not a specific version. Version-level provisioned concurrency
  is lost when you re-point the alias.

## Configuration dependency graph (novel heuristic)

Lambda alias configurations are NOT independent. Many settings are
immutable after creation; others silently break traffic shifting or
provisioned concurrency. Use this graph to sequence provisioning
and debug "why is my alias not getting provisioned concurrency?"
later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Published version | function exists + code deployed | version numbers are IMMUTABLE and auto-incremented | alias target |
| Alias | published version exists | alias name is immutable; version/weights are mutable | stable invocation target |
| Traffic weights | two published versions exist | weights must sum to 100%; shifting is progressive | canary/linear deployment |
| API Gateway integration | alias ARN with qualifier | changing the function behind the alias requires updating the API Gateway integration method | stable API endpoint |
| CloudWatch alarm | alias ARN (metric dimension) | alarm scoped to alias tracks only that version's errors | per-version monitoring |
| Provisioned concurrency | alias or version exists | **on alias: stable through traffic shifts**; on version: lost when alias re-points | cold-start elimination |
| SnapStart | function configured for SnapStart + published version | SnapStart snapshots are per-version; alias routing respects this | fast startup (JVM, Python) |
| Alias routing config | `UpdateAlias` with RoutingConfig | canary/linear weights are set on the alias, not the function | progressive rollout |

**The immutable rows are the ones a baseline model misses.**
Published version numbers are immutable and auto-incremented. Alias
names are immutable (must delete and re-create to rename). The
procedure below forces an explicit decision on each before the
`create-alias` call.

**Cross-dependency gotchas:**
- An alias CANNOT point to `$LATEST` for production traffic. It must
  point to a published version. Pointing to `$LATEST` means the
  alias target changes on every function update, defeating traffic
  shifting.
- Provisioned concurrency on a version is lost when the alias re-
  points. Always configure provisioned concurrency on the ALIAS,
  not the version.
- API Gateway integration uses the alias ARN with qualifier (e.g.,
  `function:prod`). If the alias is deleted, the API Gateway method
  breaks silently.
- SnapStart snapshots are per-version. When you shift traffic, each
  version has its own snapshot. The alias routes to the correct
  snapshot automatically.
- CloudWatch metrics with alias qualifier track only that alias's
  invocations. Without the qualifier, metrics are aggregated across
  all versions and `$LATEST`.

## Expert heuristic: weighted traffic shifting lifecycle

Traffic shifting is NOT a single API call. It is a progressive
rollout that shifts weight from one version to another over time.
A baseline model says "update the alias"; this heuristic explains
the full lifecycle.

```text
Publish version N (new code)
  → aws lambda publish-version
  → Version N is now immutable and has a version number

Alias currently points 100% to version N-1
  → Create/update alias to shift 10% to version N (canary)
  → aws lambda update-alias --routing-config AdditionalVersionWeights={"N":0.1}
  → 90% traffic → version N-1, 10% → version N

Monitor CloudWatch alarms for version N (Errors, Throttles, Duration)
  → If healthy: progressively shift 25% → 50% → 100% to version N
  → If unhealthy: rollback by shifting 100% back to version N-1

Final state: alias points 100% to version N
  → aws lambda update-alias --function-version N --routing-config {}
  → Remove routing config; alias is now a simple pointer to N
```

**Key implication:** Traffic shifting requires TWO published
versions. You cannot shift traffic to `$LATEST` — only to a
published version. This is the #1 cause of "why can't I set a
weight?" errors: the target version does not exist.

**Canary vs linear:**
- **Canary:** small initial burst (e.g., 10%) then jump to 100%.
  Good for fast validation with rollback safety.
- **Linear:** gradual increment (e.g., 10% every 5 minutes) until
  100%. Good for high-traffic functions where a sudden 10% shift
  is significant.
- **All-at-once (no shifting):** alias directly points 100% to the
  new version. No safety net. Not recommended for production.

**Rollback:** to rollback, set the weight back to the old version.
This is instant — no redeployment needed. This is the primary
advantage of alias-based traffic shifting over CodeDeploy-based
deployments.

## Expert heuristic: provisioned concurrency on alias vs version

Provisioned concurrency eliminates cold starts by pre-initializing
execution environments. A baseline model puts it on the function;
the correct approach is to put it on the ALIAS.

| Target | Behavior during traffic shift | Recommendation |
|---|---|---|
| Alias | Provisioned capacity follows the alias. As traffic shifts, provisioned environments serve the new version. Stable through rollouts. | **RECOMMENDED** |
| Version | Provisioned capacity is bound to that version number. When the alias re-points, the provisioned capacity is on the OLD version, not the new one. | Avoid for traffic-shifting scenarios |
| Function (publish) | Provisioned capacity applies to a specific published version. Same issue as version-level. | Same as version |
| $LATEST | Not supported. Provisioned concurrency cannot be configured on $LATEST. | Never use |

**Configuration on alias:**
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

**Key rule:** The `--qualifier` parameter is the ALIAS name (e.g.,
`prod`), not a version number. This binds provisioned concurrency
to the alias, and it follows the alias as traffic shifts.

**Cost implication:** Provisioned concurrency is billed regardless
of invocations. You pay for the pre-initialized environments even
if no traffic arrives. Right-size based on steady-state traffic,
not peak. Use Application Auto Scaling to adjust dynamically.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Lambda access | Cannot provision without it | `aws sts get-caller-identity` |
| Region selected | Lambda is region-scoped | `aws configure get region` |
| Lambda function exists | Alias cannot point to a non-existent function | `aws lambda get-function --function-name <name>` |
| Published version exists | Alias MUST point to a published version, not $LATEST | `aws lambda list-versions-by-function --function-name <name>` |
| Alias name identified | Alias names are immutable after creation | Provide a name (e.g., prod, staging, canary) |
| IAM execution role valid | Function must have a valid role | `aws lambda get-function-configuration --function-name <name>` |
| Two versions (for traffic shifting) | Weighted aliases require two published versions | `aws lambda list-versions-by-function` |
| SnapStart enabled on function (if applicable) | SnapStart must be configured before alias-based routing | `aws lambda get-function-configuration --function-name <name> --query SnapStart` |
| API Gateway API exists (if integrating) | Stage must reference an existing API | `aws apigateway get-rest-apis` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Published version requirement

An alias MUST point to a published version. You cannot create an
alias that points to `$LATEST` for production traffic.

**Why published versions matter:**
- Published versions are IMMUTABLE snapshots of the function code
  and configuration at publish time.
- Version numbers are auto-incremented (1, 2, 3, ...).
- `$LATEST` is mutable — it changes on every update. Aliases pointing
  to `$LATEST` are unstable.
- Traffic shifting requires published versions: you cannot shift
  weight to `$LATEST`.

**Publish a version:**
```bash
NEW_VERSION=$(aws lambda publish-version \
  --function-name my-function \
  --query Version --output text)

echo "Published version: $NEW_VERSION"
```

**Common mistake:** updating the function code and immediately
creating an alias without publishing a version first. The alias
has nothing stable to point to. Always `publish-version` before
`create-alias`.

## Step 2 — Alias creation

An alias is a named pointer to a specific published version. It
provides a stable invocation ARN that consumers (API Gateway,
EventBridge, etc.) can reference.

**Create an alias:**
```bash
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --description "Production alias"
```

**Alias ARN format:**
```
arn:aws:lambda:us-east-1:123456789012:function:my-function:prod
```

The qualifier `:prod` is the alias name. Consumers invoke the
function using this ARN. When you update the alias to point to a
new version, consumers automatically see the new version — no
endpoint change needed.

**Key rules:**
- Alias names are immutable. To rename, delete and re-create.
- An alias can point to only ONE version at a time (without routing
  config). With routing config, it splits traffic between two.
- Each function can have up to 1,000 aliases.
- Alias description is mutable.

## Step 3 — Traffic shifting (weighted aliases)

Traffic shifting splits invocations between two published versions.
This enables canary and linear deployments without endpoint changes.

**Set canary traffic (10% to new version):**
```bash
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config AdditionalVersionWeights='{"6":0.1}'
```

This sends 90% of traffic to version 5 and 10% to version 6.

**Progressively shift (25% → 50% → 100%):**
```bash
# 25%
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --routing-config AdditionalVersionWeights='{"6":0.25}'

# 50%
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --routing-config AdditionalVersionWeights='{"6":0.5}'

# 100% (finalize — remove routing config)
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6 \
  --routing-config '{}'
```

**Rollback (shift back to old version):**
```bash
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config '{}'
```

**Common mistake:** trying to shift traffic to `$LATEST` instead of
a published version. Traffic shifting requires a specific version
number in `AdditionalVersionWeights`. `$LATEST` is not a version.

## Step 4 — API Gateway stage integration

API Gateway integrates with Lambda via the alias ARN. The alias
provides a stable invocation target that survives version updates.

**Integration setup:**
```bash
# API Gateway method integration uses the alias ARN
# arn:aws:lambda:us-east-1:123456789012:function:my-function:prod

# Grant API Gateway permission to invoke the alias
aws lambda add-permission \
  --function-name my-function:prod \
  --statement-id apigateway-prod \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123456789012:abc123/*/GET/hello"
```

**Key rules:**
- The integration URI must include the alias qualifier:
  `arn:...:function:my-function:prod`
- Without the qualifier, API Gateway invokes `$LATEST`, bypassing
  the alias entirely. This defeats traffic shifting.
- Permission must be granted to the ALIAS, not just the function.
  Use `function-name:alias` in `add-permission`.
- When the alias shifts traffic, API Gateway automatically routes
  to the weighted versions — no API Gateway change needed.

**Common mistake:** configuring the API Gateway integration with
the function ARN (no qualifier). This invokes `$LATEST` directly,
bypassing the alias and all traffic-shifting logic. Always include
the alias qualifier in the integration URI.

## Step 5 — CloudWatch alarm per alias

CloudWatch metrics for Lambda are scoped by the `FunctionName` and
`Resource` dimensions. To monitor a specific alias, use the alias
ARN as the `Resource` dimension.

**Create an alarm scoped to an alias:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "my-function-prod-errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function Name=Resource,Value=my-function:prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:alerts"
```

**Key dimensions:**
- `FunctionName`: the function name (e.g., `my-function`).
- `Resource`: the function + qualifier (e.g., `my-function:prod`).
  Without this, metrics are aggregated across all versions.

**Metrics available per alias:**
- `Errors`: invocation errors scoped to this alias.
- `Throttles`: throttled invocations scoped to this alias.
- `Duration`: execution time scoped to this alias.
- `Invocations`: total invocations scoped to this alias.
- `ConcurrentExecutions`: concurrent executions (use alias qualifier).
- `ProvisionedConcurrencyInvocations` / `ProvisionedConcurrencySpilloverInvocations`.

**Common mistake:** creating the alarm without the `Resource`
dimension. The alarm aggregates across all versions and `$LATEST`,
making it impossible to detect errors specific to the alias.

## Step 6 — Provisioned concurrency on alias

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts. Configure it on the ALIAS so it follows
traffic shifts.

**Configure provisioned concurrency on an alias:**
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

**Verification:**
```bash
aws lambda get-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod
```

**Key rules:**
- The `--qualifier` is the alias name (e.g., `prod`), NOT a version
  number. This is what makes provisioned concurrency follow the alias.
- Provisioned concurrency is billed regardless of invocations. Right-
  size based on steady-state, not peak.
- Use Application Auto Scaling to adjust dynamically based on
  utilization (ProvisionedConcurrencyUtilization metric).

**Auto Scaling for provisioned concurrency:**
```bash
# Register as a scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id function:my-function:prod \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity 2 \
  --max-capacity 20

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --policy-name prod-provisioned-scaling \
  --service-namespace lambda \
  --resource-id function:my-function:prod \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "LambdaProvisionedConcurrencyUtilization"
    }
  }'
```

## Step 7 — Lambda SnapStart

SnapStart reduces cold-start times for supported runtimes (Java,
Python) by restoring pre-initialized execution environments from
snapshots. SnapStart is configured on the FUNCTION, but snapshots
are per-VERSION. The alias routes to the correct snapshot.

**Enable SnapStart on the function:**
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --snap-start ApplyOn=PublishedVersions
```

**Publish a new version (SnapStart creates a snapshot for this version):**
```bash
aws lambda publish-version \
  --function-name my-function
```

**Verify SnapStart status:**
```bash
aws lambda get-function-configuration \
  --function-name my-function \
  --qualifier 5 \
  --query 'SnapStart'
```

**Key rules:**
- SnapStart must be enabled on the function BEFORE publishing
  versions. Existing versions do NOT get snapshots retroactively.
- Each published version gets its OWN snapshot. The alias routes
  to the correct snapshot automatically.
- SnapStart snapshots are restored in milliseconds (vs seconds for
  full JVM initialization).
- SnapStart is available for `java11`, `java17`, `java21`, and
  `python3.12` runtimes (as of 2026).

**Common mistake:** enabling SnapStart after publishing the version.
The version does not get a snapshot. You must enable SnapStart on
the function first, then publish a new version. The new version
will have the snapshot.

**SnapStart + traffic shifting:** when you shift traffic between
two versions, each version has its own snapshot. There is no
additional configuration needed — the alias handles routing to
the correct snapshot.

## Step 8 — Recent features

**Recent AWS features (2023-2026):**

- **SnapStart for Python (2025-2026):** SnapStart extended beyond
  Java to Python 3.12. Same snapshot-based cold-start elimination
  for Python workloads.

- **SnapStart for Java 21 (2024-2025):** Extended SnapStart support
  to the Java 21 runtime.

- **Provisioned concurrency with Auto Scaling (2023-2024):**
  Application Auto Scaling now supports target-tracking policies for
  provisioned concurrency based on utilization. Dynamically adjusts
  provisioned environments without manual intervention.

- **CloudWatch Lambda Insights per alias (2023-2024):** Enhanced
  CloudWatch metrics with per-alias granularity, including memory
  utilization, CPU time, and cold-start counts scoped to each alias.

- **Lambda recursive detection (2023-2024):** AWS detects recursive
  Lambda loops and stops them automatically. Works with alias-based
  invocations.

- **Alias-based AWS X-Ray tracing (2023-2024):** X-Ray traces now
  include the alias qualifier, enabling per-alias trace analysis
  without separate instrumentation.

## NEVER do these things

1. **NEVER point a production alias to `$LATEST`.** `$LATEST` is
   mutable and changes on every function update. The alias target
   would change silently, bypassing traffic-shifting safety. Always
   point to a published version.

2. **NEVER configure provisioned concurrency on a version number
   instead of an alias.** Version-level provisioned concurrency is
   lost when the alias re-points to a new version. Always use
   alias-level provisioned concurrency (`--qualifier <alias-name>`).

3. **NEVER shift traffic to `$LATEST`.** Traffic shifting requires
   a published version number in `AdditionalVersionWeights`. `$LATEST`
   is not a version and will cause an API error.

4. **NEVER configure API Gateway integration without the alias
   qualifier.** Without `:prod` (or the alias name), API Gateway
   invokes `$LATEST` directly, bypassing the alias and all traffic-
   shifting logic.

5. **NEVER enable SnapStart after publishing the version.** SnapStart
   snapshots are created at publish time. Existing versions do NOT
   get snapshots retroactively. Enable SnapStart on the function
   first, then publish a new version.

## Output format

```text
LAMBDA_ALIAS: <function-name>:<alias-name> (version <n>, weight <n>%)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Function: <function-name> (exists in <region>)
  [✓|✗] Published version: <n> (immutable snapshot)
  [✓|✗] Alias: <alias-name> → version <n>
  [✓|✗] Traffic shifting: <canary/linear> (version <old> <old-weight>% → version <new> <new-weight>%) | none
  [✓|✗] API Gateway integration: <api-id> stage <stage> → alias <alias-name> | N/A
  [✓|✗] CloudWatch alarm: <alarm-name> scoped to <function-name>:<alias-name> | N/A
  [✓|✗] Provisioned concurrency: <n> executions on alias <alias-name> | disabled
  [✓|✗] SnapStart: enabled (version <n> has snapshot) | disabled | not applicable
  [✓|✗] Auto Scaling: target=<n>% utilization, min=<n>, max=<n> | disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws lambda get-alias --function-name <function-name> --name <alias-name>
  aws lambda get-provisioned-concurrency-config --function-name <function-name> --qualifier <alias-name>
  aws cloudwatch describe-alarms --alarm-names <alarm-name>
```

### Worked example — alias with canary traffic shift and provisioned concurrency

```text
LAMBDA_ALIAS: my-function:prod (version 5, weight 90%; version 6, weight 10%)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Function: my-function (exists in us-east-1)
  [✓] Published version: 5 (current), 6 (canary)
  [✓] Alias: prod → version 5 (90%) + version 6 (10%)
  [✓] Traffic shifting: canary (version 5 90% → version 6 10%)
  [✓] API Gateway integration: abc123 stage prod → alias prod
  [✓] CloudWatch alarm: my-function-prod-errors scoped to my-function:prod
  [✓] Provisioned concurrency: 10 executions on alias prod
  [✓] SnapStart: disabled
  [✓] Auto Scaling: target=70% utilization, min=2, max=20
  [✓] Tags: Environment=production, Service=api
VERIFICATION_COMMANDS:
  aws lambda get-alias --function-name my-function --name prod
  aws lambda get-provisioned-concurrency-config --function-name my-function --qualifier prod
  aws cloudwatch describe-alarms --alarm-names my-function-prod-errors
```

## Error handling

### "InvalidParameterValueException: function version does not exist"
- The version number in `--function-version` does not exist. Verify
  with `aws lambda list-versions-by-function`. Publish a version
  first with `aws lambda publish-version`.

### "ResourceConflictException: alias already exists"
- Alias names are unique per function. Delete the existing alias
  (`aws lambda delete-alias`) before re-creating, or use
  `update-alias` to modify the existing one.

### Provisioned concurrency stuck in `PROGRESSING` or `FAILED`
- Verify the alias exists and points to a valid version. Check IAM
  permissions for the service-linked role. Verify the account's
  concurrent execution limit (`aws lambda get-account-settings`).

### Traffic shifting weight not changing
- Verify the version in `AdditionalVersionWeights` is a published
  version (not `$LATEST`). Verify the alias already points to the
  primary version. Weights must sum to 1.0 (100%).

### API Gateway invoking `$LATEST` instead of the alias
- The integration URI is missing the alias qualifier. Update the
  integration to include `:prod` (or the alias name). Re-deploy the
  API Gateway stage.

### SnapStart snapshot not created
- SnapStart was enabled AFTER the version was published. Enable
  SnapStart on the function first (`update-function-configuration`),
  then publish a new version. The new version will have the snapshot.

## Domain

AWS CloudOps / Lambda Alias Provisioning & Serverless Traffic
Management.

## AWS documentation

- **Lambda aliases** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html
- **Traffic shifting** — https://docs.aws.amazon.com/lambda/latest/dg/traffic-shifting.html
- **Provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html
- **SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html
- **API Gateway + Lambda aliases** — https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-integrations.html
- **CloudWatch Lambda metrics** — https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html
- **Auto Scaling for provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html#pc-auto-scaling
