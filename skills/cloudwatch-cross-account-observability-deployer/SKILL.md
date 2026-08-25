---
name: cloudwatch-cross-account-observability-deployer
description: 'Provisions CloudWatch cross-account observability via Observability Access Manager (OAM) — creates the monitoring account sink, attaches source accounts, configures the link (metrics / logs / traces / Application Signals sharing), wires IAM roles, and validates the topology. Wires Amazon Managed Grafana cross-account data-source queries, integrates CloudWatch cross-account with AMP (Managed Prometheus), and surfaces cross-account Application Signals service maps. Emits a READY_TO_DEPLOY checklist. Use when creating an OAM sink, linking source accounts, sharing CloudWatch metrics / logs / traces across accounts, attaching AMP workspaces cross-account, enabling cross-account Application Signals, or wiring Managed Grafana across accounts. Triggers: cloudwatch cross-account, observability access manager, oam, oam sink, oam link, cross-account observability, monitoring account, cross-account metrics / logs / traces / application signals, managed grafana cross-account, amp cross-account, cloudwatch multi-account.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with oam, cloudwatch, iam, logs, xray, application-signals, amp, grafana, and organizations access. Works with Terraform aws_oam_sink / aws_oam_link, CloudFormation AWS::Oam::Sink / AWS::Oam::Link, and AWS CloudFormation StackSets for multi-account link deployment.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudwatch, oam, cross-account, observability, deploy
  dependencies: aws-orchestrator
  keywords: aws, cloudwatch, oam, observability-access-manager, cross-account, multi-account, observability, cloudops, deploy, provisioning, managed-grafana, amp, managed-prometheus, application-signals
  when_to_use: Invoke when the user wants to create a CloudWatch cross-account observability topology — a monitoring (aggregator) account with an OAM sink and one or more source accounts with OAM links sharing metrics, logs, traces, or Application Signals data. Use for provisioning the OAM sink, attaching source accounts, scoping the sharing model (which namespaces, which log groups, which X-Ray services), wiring Amazon Managed Grafana to query across accounts via the sink, attaching AMP (Managed Prometheus) workspaces to the OAM sink, or enabling cross-account Application Signals service maps. Do NOT invoke for single-account CloudWatch dashboards / alarms (cloudwatch-dashboard-deployer / cloudwatch-alarm-operator), for IAM cross-account role assumption patterns (iam-role-deployer), for CloudTrail org trails (cloudtrail-org-trail-auditor), or for single-account Application Signals enablement (cloudwatch-application-signals-deployer).
---

# CloudWatch Cross-Account Observability Deployer

An AWS CloudOps agent skill that provisions CloudWatch cross-account
observability via Observability Access Manager (OAM). Creates the
monitoring account sink, attaches source accounts via OAM links,
configures the sharing model (metrics, logs, traces, Application
Signals), and validates the resulting topology with
`READY_TO_DEPLOY` status. Wires Amazon Managed Grafana and AMP
cross-account data-source integration.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the topology order matters | "Reasoning framework" |
| What to verify before linking | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Sink creation, link attachment, sharing scopes | "Deployment procedure" Steps 1-5 |
| Managed Grafana and AMP cross-account wiring | "Deployment procedure" Steps 6-7 |
| Cross-account Application Signals | "Deployment procedure" Step 8 |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| Sharing scopes, IAM policy templates, multi-org | `references/sharing-scopes-and-iam-guide.md` |

## STRICT output contract

When this skill is invoked with a CloudWatch cross-account
observability request (sink creation, source account linking,
sharing scope, Grafana integration, AMP cross-account, or a
partial existing OAM topology), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in "Output format" using the
literal all-caps labels `MONITORING_ACCOUNT:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block
as the first lines of the response.

### Required output structure

1. `MONITORING_ACCOUNT: <account-id>` — the aggregator account
   hosting the OAM sink.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `MONITORING_ACCOUNT:`** — the first
  non-empty line MUST be `MONITORING_ACCOUNT:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK".
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING; the operator needs commands to verify
  gaps.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response. Put deeper explanation
  in `references/`.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`, `[WARN]`, or emoji.

### Perfect example (copy the shape exactly)

```text
MONITORING_ACCOUNT: 111122223333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Monitoring account sink — arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
  [✓]      Sink policy — allows source accounts 444455556666, 777788889999 to attach
  [✓]      Source link (444455556666) — link/payloads-prod-app attached to sink
  [✓]      Source link (777788889999) — link/payloads-payments-app attached to sink
  [✓]      Sharing — MetricConfiguration: AWS/EC2, AWS/ECS, AWS/ApplicationSignals (ALL)
  [✓]      Sharing — LogGroupConfiguration: /aws/ecs/prod-app, /aws/lambda/payments-api
  [✓]      Sharing — TraceConfiguration: X-Ray services api-gateway, checkout, payments
  [✓]      IAM — source accounts hold oam:CreateLink and oam:PutSinkPolicy on the sink ARN
  [✓]      Managed Grafana — workspace grafana-prod has CloudWatch data source querying sink
  [✓]      AMP workspace — amp-prod attached as cross-account data source
  [✓]      Cross-account Application Signals — service map aggregates across both source accounts
  [OPTIONAL] AWS Organizations managed link — use org-wide sink policy for > 50 source accounts
  [OPTIONAL] CloudWatch Logs account-level data protection — mask PII in shared log groups
VERIFICATION_COMMANDS:
  aws oam list-sinks --region us-east-1
  aws oam get-sink --identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
  aws oam list-attached-links --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink
  aws oam list-links --region us-east-1
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --region us-east-1
  aws logs describe-log-groups --log-group-name-prefix /aws/ecs --region us-east-1
  aws grafana list-workspaces --region us-east-1
  aws amp list-workspaces --region us-east-1
```

## Reasoning framework (why the topology order matters)

Cross-account observability via OAM has **dependency and ordering
constraints**. Skipping or misordering causes silent gaps — the
monitoring account sees some accounts but not others, certain
namespaces never appear, or Managed Grafana queries return empty:

1. **Sink FIRST, in the monitoring account** — `oam create-sink`
   provisions the aggregation point. Every link references the
   sink ARN. The sink must exist before any source account can
   call `oam create-link`.
2. **Sink policy controls who can attach** — the sink policy is a
   resource-based policy. Without an entry for a source account,
   `oam create-link` from that account returns `AccessDenied`.
3. **Source account creates the link** — the link is created in
   the SOURCE account, not the monitoring account. The source
   account must have an IAM identity with `oam:CreateLink`
   permission scoped to the sink ARN. Calling `oam create-link`
   from the monitoring account fails.
4. **Sharing scope declared at link creation** —
   `MetricConfiguration`, `LogGroupConfiguration`, and
   `TraceConfiguration` are set on the link at creation. Changing
   scope later requires `update-link`. Over-scoping floods the
   monitoring account; under-scoping silently hides the metric.
5. **IAM `oam:PutSinkPolicy` in the monitoring account** — to
   authorize a new source account, the monitoring account updates
   the sink policy. Source accounts need `oam:CreateLink` only.
6. **Managed Grafana queries via the sink role** — Grafana does
   NOT query each source account individually. It assumes a role
   in the monitoring account that has read access to the sink.
7. **AMP cross-account uses a different attachment model** — AMP
   workspace cross-account query rules are configured on the
   workspace, NOT via OAM. OAM applies to CloudWatch metrics,
   logs, and traces. For AMP, use cross-account IAM roles on the
   workspace.
8. **Application Signals cross-account requires the link plus
   enablement in each source** — OAM shares the
   `AWS/ApplicationSignals` namespace, but the source workload
   must have Application Signals enabled separately. OAM transports
   the metrics; it does not flip the enable bit.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Two or more AWS accounts** | One monitoring account, one or more source accounts. | `aws sts get-caller-identity` in each |
| **Monitoring account IAM principal** | Needs `oam:CreateSink`, `oam:PutSinkPolicy`, `oam:GetSink`, `oam:ListSinks`, `oam:ListAttachedLinks`. | `aws iam list-attached-role-policies --role-name <role>` |
| **Source account IAM principal** | Needs `oam:CreateLink`, `oam:UpdateLink`, `oam:GetLink`, `oam:DeleteLink` scoped to the sink ARN. | Same, in source account |
| **Sink policy resource principal entry** | MUST list each source account principal before `CreateLink` succeeds. | `aws oam get-sink-policy --sink-identifier <arn>` |
| **AWS Organizations (optional)** | Org-managed sink policies simplify large fleets. | `aws organizations describe-organization` |
| **CloudWatch Logs groups exist** | LogGroupConfiguration filter must match existing log groups. | `aws logs describe-log-groups --region <r>` |
| **X-Ray services emitting traces** | TraceConfiguration filter must match services that exist. | `aws xray get-summary --region <r>` |
| **Application Signals enabled in each source** (optional) | Required for cross-account Application Signals correlation. | `aws application-signals list-services --region <r>` |
| **Managed Grafana / AMP workspaces** (optional) | Required for unified cross-account dashboards / Prometheus queries. | `aws grafana list-workspaces`, `aws amp list-workspaces` |

## Deployment procedure (apply in order)

### Step 1: Create the OAM sink in the monitoring account

The sink is the aggregation point, Region-scoped. Create it in the
monitoring account with a descriptive name.

```bash
# Run from the MONITORING account (111122223333)
aws oam create-sink \
  --name ProdObservabilitySink \
  --tags Environment=prod,Team=observability \
  --region us-east-1
```

The response returns a sink ARN like
`arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink`.
Capture it — every downstream command uses it. The default sink
policy allows only the monitoring account; update it (Step 2).

### Step 2: Authorize source accounts via the sink policy

The sink policy is a resource-based policy. Add each source
account principal. Use the `aws:PrincipalAccount` condition to
scope to specific accounts, or `aws:PrincipalOrgID` for an
org-wide policy.

Step 2 sink-policy CLI payload (sink-policy.json heredoc + put-sink-policy) moved verbatim to [references/deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when authoring the resource-based sink policy; the Organizations `aws:PrincipalOrgID` variant stays below.

For an Organizations-managed fleet, prefer
`aws:PrincipalOrgID` over enumerating accounts:

```json
"Principal": { "AWS": "*" },
"Condition": { "StringEquals": { "aws:PrincipalOrgID": "o-abcdef1234" } }
```

This auto-includes new accounts as they join the org, but the
source account IAM role still needs `oam:CreateLink` on the sink
ARN.

### Step 3: Create the source account IAM role

Each source account needs an IAM principal with permissions to
call `oam:CreateLink` on the sink ARN. Use a dedicated role; do
not attach to a broad administrative role.

Step 3 source-account IAM role CLI payload (trust + permission documents + create-role + put-role-policy) moved verbatim to [references/deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when creating the sink-scoped OAMLinkRole; keep the policy resource-locked to the sink ARN.

Resource-lock the policy to the specific sink ARN. A wildcard
(`oam:CreateLink: *`) lets the source attach to any sink in any
account, which is rarely intended.

### Step 4: Create the OAM link from the source account

The link is created in the SOURCE account. The link declares what
resource types (metrics, log groups, traces, Application Signals)
to share and the scope (which namespaces, which log group names,
which X-Ray services).

Step 4 OAM link CLI payload (link-config.json heredoc + create-link) moved verbatim to [references/deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when authoring Metric/LogGroup/Trace filters; the Filter-language notes stay below.

The `Filter` language supports: `Namespace IN (...)`,
`Service("...")`, `prefix("...")`, `OR`, `AND`. The filter is
case-sensitive. Use `AWS::CloudWatch::Metric` for CloudWatch
metrics, `AWS::Logs::LogGroup` for log groups, `AWS::XRay::Trace`
for X-Ray traces, and `AWS::ApplicationSignals::Service` for
Application Signals service map data. Repeat for each source
account.

### Step 5: Verify the link is attached

From the monitoring account, confirm each link landed:

```bash
aws oam list-attached-links \
  --sink-identifier arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --region us-east-1

aws oam get-link \
  --identifier arn:aws:oam:us-east-1:444455556666:link/prod-app-link-abcdef \
  --region us-east-1
```

A link that is `CREATED` but not `ATTACHED` means the source
account created the link but the sink policy rejected the resource
types; check the sink policy condition `oam:ResourceTypes`.

### Step 6: Wire Managed Grafana to query via the sink

Managed Grafana does not query each source account directly.
Grafana assumes a role in the monitoring account that has read
access to CloudWatch (and the sink's data). The sink aggregates
cross-account metrics, logs, and traces.

1. In the monitoring account, create `GrafanaCrossAccountReadRole`
   with `sts:AssumeRole` trust allowing the Grafana workspace
   service principal.
2. Attach a policy with `cloudwatch:GetMetricData`,
   `cloudwatch:GetMetricStatistics`, `cloudwatch:ListMetrics`,
   `logs:DescribeLogGroups`, `logs:FilterLogEvents`,
   `logs:GetLogEvents`, `xray:GetTraceSummaries`,
   `xray:GetTraceGraph`, `oam:GetSink`, `oam:ListAttachedLinks`.
3. In the Managed Grafana workspace, add a CloudWatch data source
   with the role ARN and Region. Add an X-Ray data source with
   the same role ARN.

```bash
aws grafana update-workspace \
  --workspace-id g-abcdef1234 \
  --workspace-data-sources '[{"Type":"CLOUDWATCH","Settings":{"accountID":"111122223333","roleArn":"arn:aws:iam::111122223333:role/GrafanaCrossAccountReadRole"}},{"Type":"XRAY"}]' \
  --region us-east-1
```

In Grafana dashboards, the cross-account data appears as a single
CloudWatch / X-Ray source. The `accountId` field in queries
defaults to the monitoring account; the sink transparently
returns aggregated data.

### Step 7: Attach AMP workspace for cross-account Prometheus

AMP (Managed Prometheus) cross-account query uses workspace
query-rule IAM roles, NOT OAM. To let the monitoring account or
Grafana query an AMP workspace in a source account:

Step 7 AMP cross-account query-rule CLI payload (amp-query-rule.json trust policy + create-workspace) moved verbatim to [references/deployment-cli-commands.md](references/deployment-cli-commands.md).
Load on demand when wiring AMP workspace cross-account queries; remember OAM does NOT proxy AMP.

Then in Grafana, add a Prometheus data source pointing at the AMP
workspace endpoint with the cross-account role ARN. Grafana
assumes the role to query the workspace. OAM does NOT proxy AMP —
the workspace remains in the source account.

### Step 8: Enable cross-account Application Signals

Application Signals cross-account requires: (1) Application
Signals enabled in EACH source account for the workload (EKS,
ECS, Lambda, EC2) — use the
`cloudwatch-application-signals-deployer` skill per source; (2)
the OAM link in each source includes
`AWS::ApplicationSignals::Service` in `ResourceTypes`; (3) the
sink policy allows the source account principal to share
`AWS::ApplicationSignals::Service`.

Once linked, the monitoring account sees the
`AWS/ApplicationSignals` namespace with metrics and service maps
aggregated across source accounts. Each service is dimensioned by
`ServiceName`, `Environment`, `Type`, and includes a derived
`SourceAccount` dimension for filtering.

```bash
aws cloudwatch list-metrics \
  --namespace AWS/ApplicationSignals \
  --region us-east-1
```

If the namespace is empty in the monitoring account, the cause is
almost always: Application Signals not enabled on the workload in
the source; link missing `AWS::ApplicationSignals::Service`; or
the workload not yet discovered (`list-services` returns empty in
the source account).

### Step 9: Verify cross-account data flows

Within 1-5 minutes of link creation, cross-account data should
appear in the monitoring account:

```bash
aws cloudwatch list-metrics --namespace AWS/EC2 --region us-east-1
aws logs describe-log-groups --log-group-name-prefix /aws/ecs/prod-app --region us-east-1
aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) --region us-east-1
```

If data does not appear within 15 minutes, the cause is almost
always: link filter scope excludes the namespace / log group /
service; sink policy condition
`ForAllValues:StringEquals oam:ResourceTypes` excludes the
resource type you expected; IAM role in the source account does
NOT include the resource type in `oam:CreateLink` permission
scope; or filter uses uppercase where the actual name is
lowercase (filters are case-sensitive).

### Step 10: Tag, alarm, and visualize cross-account

Tag the sink for cost allocation. Build dashboards and alarms on
the aggregated metrics in the monitoring account:

```bash
aws oam tag-resource \
  --resource-arn arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink \
  --tags team=observability,env=prod

aws cloudwatch put-metric-alarm \
  --alarm-name cross-account-checkout-error-spike \
  --namespace AWS/ApplicationSignals \
  --metric-name Error \
  --dimensions Name=ServiceName,Value=checkout \
  --period 300 --evaluation-periods 2 \
  --threshold 50 --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:111122223333:oncall
```

Open the CloudWatch console in the monitoring account to confirm
the cross-account namespace, log groups, and X-Ray service map
populate. Use the "Account" column in the console to confirm each
source account is represented.

## Resource-type sharing matrix

| Resource type | What it shares | Filter language |
|---|---|---|
| `AWS::CloudWatch::Metric` | CloudWatch metrics by namespace | `Namespace IN (...)`, `prefix("...")`, `AND`, `OR` |
| `AWS::Logs::LogGroup` | CloudWatch Logs groups | log group name patterns: `name OR name OR prefix("...")` |
| `AWS::XRay::Trace` | X-Ray traces by service | `Service("name") OR Service("name")` |
| `AWS::ApplicationSignals::Service` | Application Signals services | service name patterns |

## Edge-case handling

Edge-case catalog (CREATED-not-ATTACHED links, case-sensitive filters, empty log groups, disconnected service maps, missing Application Signals, empty Grafana queries, AMP 403, policy-change effects, cross-Region) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a linked account's data does not appear in the monitoring account.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when choosing between new and legacy OAM mechanisms.

## NEVER (top 5 — full list in references)

- NEVER create the link from the monitoring account. The link is
  created in the SOURCE account and references the sink ARN.
  Creating from the monitoring account returns
  `InvalidParameterException`.
- NEVER use a wildcard sink policy (`"Principal": {"AWS": "*"}`)
  without a condition. An open sink policy lets ANY AWS account
  attach a link to your sink. Always scope with
  `aws:PrincipalAccount`, `aws:PrincipalOrgID`, or explicit ARNs.
- NEVER omit the `oam:ResourceTypes` condition on the sink policy
  when you want to restrict resource types. Without the condition,
  source accounts can share ANY resource type.
- NEVER resource-lock the source account IAM policy to
  `oam:CreateLink: *`. A wildcard lets the source attach to sinks
  in other accounts. Scope to the specific sink ARN.
- NEVER configure per-account Managed Grafana data sources for
  OAM-shared data. Grafana queries the monitoring account role
  which reads via the sink. Use a single data source per Region.

## Expert heuristic — designing cross-account observability topology

Expert heuristic — designing cross-account observability topology moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning multi-account / multi-Region observability layouts.

## Pre-flight safety checks (run before any OAM CLI)

Pre-flight safety checks (sink existence, sink policy principals, source IAM scoping, Region pinning, resource-type inventory) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before running any OAM CLI.

## Output format — MANDATORY literal labels

When invoked with a CloudWatch cross-account observability
request, your ENTIRE response MUST be the checklist block below.
The labels are **case-sensitive all-caps keywords** — write them
EXACTLY as shown. Do NOT write a preamble. Start with
`MONITORING_ACCOUNT:` and stop after the `VERIFICATION_COMMANDS:`
block.

```text
MONITORING_ACCOUNT: <account-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Monitoring account sink — <sink-arn>
  [✓]      Sink policy — allows source accounts <list> to attach
  [✓]      Source link (<account-id>) — <link-arn> attached to sink
  [✓]      Sharing — MetricConfiguration: <namespaces>
  [✓]      Sharing — LogGroupConfiguration: <log-group-patterns>
  [✓]      Sharing — TraceConfiguration: <xray-services>
  [✓]      Sharing — ApplicationSignals services <list>
  [✓]      IAM — source accounts hold oam:CreateLink on <sink-arn>
  [✓]      Managed Grafana — workspace <id> with CloudWatch data source via <role-arn>
  [✓]      AMP workspace — <workspace-id> attached as cross-account data source
  [✓]      Cross-account Application Signals — service map aggregates across source accounts
  [OPTIONAL] AWS Organizations managed link — org-wide sink policy
  [OPTIONAL] CloudWatch Logs data protection — PII masking in shared log groups
VERIFICATION_COMMANDS:
  aws oam list-sinks --region <region>
  aws oam get-sink --identifier <sink-arn>
  aws oam list-attached-links --sink-identifier <sink-arn>
  aws oam list-links --region <region>
  aws cloudwatch list-metrics --namespace AWS/ApplicationSignals --region <region>
  aws logs describe-log-groups --log-group-name-prefix <prefix> --region <region>
  aws grafana list-workspaces --region <region>
  aws amp list-workspaces --region <region>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload
  type.
- `[INPUT NEEDED]` — prerequisite value missing; operator must
  provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite
is missing (sink does not exist, sink policy missing source
account principal, source account lacks `oam:CreateLink` on sink
ARN, Application Signals enabled in monitoring but not in source),
the verdict is `PREREQUISITES_MISSING` with each gap listed and
a `REMEDIATION:` line per gap.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — edge-case catalog, topology-design expert heuristic, and Recent AWS features (2024-2026) moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks moved from SKILL.md
- [references/deployment-cli-commands.md](references/deployment-cli-commands.md) — deep CLI sequences; now also holds the Step 2/3/4 and Step 7 payload blocks moved from SKILL.md

## Domain

AWS CloudOps / Cross-Account Observability Provisioning.

## AWS documentation

- **CloudWatch Observability Access Manager** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OAM.html
- **OAM sink management** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OAM-sink.html
- **OAM link management + filter syntax** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OAM-link.html
- **Cross-account Application Signals** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-cross-account.html
- **Managed Grafana cross-account** — https://docs.aws.amazon.com/grafana/latest/userguide/cross-account.html
- **AMP cross-account query** — https://docs.aws.amazon.com/prometheus/latest/userguide/cross-account-query.html
- **AWS CLI oam reference** — https://docs.aws.amazon.com/cli/latest/reference/oam/
- **AWS::Oam::Sink / AWS::Oam::Link CloudFormation** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-oam-sink.html

## References

- `references/deployment-cli-commands.md` — full copy-pasteable
  CLI command sequence for all 10 provisioning steps, Terraform
  equivalents, CloudFormation snippets, and StackSets templates.

- `references/sharing-scopes-and-iam-guide.md` — sharing scopes,
  sink policy templates (single, multi-account, org-wide), source
  account IAM role patterns, AMP cross-account workspace roles,
  full NEVER list, and edge-case handling.

