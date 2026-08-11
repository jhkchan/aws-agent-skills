# Sharing scopes and IAM guide — deep reference

This reference covers resource-type sharing scopes, sink policy
templates (single account, multi-account, org-wide), source
account IAM role patterns, AMP cross-account workspace roles, the
full NEVER list, and edge-case handling. Load when designing or
troubleshooting a cross-account observability topology.

## Resource-type sharing scopes

Each OAM link declares `ResourceTypes` — the categories of
telemetry the source account shares with the monitoring account.
The sink policy gates which resource types a source account may
share.

### AWS::CloudWatch::Metric

Shares CloudWatch metrics by namespace. The
`MetricConfiguration.Filter` scopes which namespaces flow.

| Filter pattern | Effect |
|---|---|
| `Namespace IN ("AWS/EC2", "AWS/ECS")` | Shares only these namespaces |
| `Namespace IN ("AWS/EC2") AND Namespace NOT IN ("AWS/ECS/Fargate")` | Include + exclude |
| `prefix("AWS/")` | All AWS namespaces (broad) |
| `"*"` | All namespaces including custom |

Filter syntax is case-sensitive. `AWS/ECS` is the canonical form;
`aws/ecs` matches nothing.

### AWS::Logs::LogGroup

Shares CloudWatch Logs log groups by name pattern. The
`LogGroupConfiguration.Filter` matches the log group name (not
the log stream).

| Filter pattern | Effect |
|---|---|
| `/aws/ecs/prod-app` | Shares one log group |
| `/aws/ecs/prod-app OR /aws/lambda/payments-api` | Shares two groups |
| `prefix("/aws/ecs/")` | Shares all log groups starting with `/aws/ecs/` |
| `"*"` | Shares ALL log groups (broad) |

Wildcards (`*`) as a filter value share everything; use
`prefix("...")` for namespace-scoped sharing. The filter matches
the log group name as created by the service or by the operator.

### AWS::XRay::Trace

Shares X-Ray trace segments by service. The
`TraceConfiguration.Filter` matches the X-Ray service name (the
segment's `service.name`).

| Filter pattern | Effect |
|---|---|
| `Service("checkout")` | Shares one service's traces |
| `Service("checkout") OR Service("payments")` | Shares two services |
| `"*"` | Shares all services' traces |

The X-Ray service map in the monitoring account aggregates the
linked services. Services NOT in the filter are invisible to the
monitoring account.

### AWS::ApplicationSignals::Service

Shares Application Signals service-level metrics (Latency, Error,
Availability, Traffic) and service map topology. The filter
matches the Application Signals service name.

Each shared service includes a derived `SourceAccount` dimension
in the monitoring account's `AWS/ApplicationSignals` namespace,
enabling per-source-account filtering in dashboards and alarms.

**Prerequisite:** Application Signals MUST be enabled in the
source account for the workload (EKS, ECS, Lambda, EC2). OAM
transports the metrics once the workload is discovered by
Application Signals. OAM does NOT enable Application Signals.

## Sink policy templates

### Single source account

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::444455556666:root" },
    "Action": ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"],
    "Resource": "*"
  }]
}
```

### Multi-account with resource-type restriction

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::444455556666:root" },
    "Action": ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"],
    "Resource": "*",
    "Condition": {
      "ForAllValues:StringEquals": {
        "oam:ResourceTypes": [
          "AWS::CloudWatch::Metric",
          "AWS::Logs::LogGroup",
          "AWS::XRay::Trace",
          "AWS::ApplicationSignals::Service"
        ]
      }
    }
  }]
}
```

The `ForAllValues:StringEquals` condition ensures the source
account can ONLY share the listed resource types. Omitting the
condition lets the source share any resource type.

### Org-wide

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "*" },
    "Action": ["oam:CreateLink", "oam:UpdateLink", "oam:DeleteLink"],
    "Resource": "*",
    "Condition": {
      "StringEquals": { "aws:PrincipalOrgID": "o-abcdef1234" }
    }
  }]
}
```

`aws:PrincipalOrgID` auto-includes new accounts joining the org.
The source account IAM role still needs `oam:CreateLink` on the
sink ARN; the sink policy opens the gate, IAM drives the action.

### Org-wide with OU restriction

```json
"Condition": {
  "StringEquals": {
    "aws:PrincipalOrgID": "o-abcdef1234",
    "aws:PrincipalOrgPaths": "o-abcdef1234/r-abcd/ou-abcd-1234/*"
  }
}
```

This restricts to a specific OU within the org, useful for
separating production vs. non-production observability.

## Source account IAM role patterns

### Minimal link role

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["oam:CreateLink", "oam:GetLink", "oam:DeleteLink"],
    "Resource": "arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink"
  }]
}
```

### CI/CD pipeline role with update permission

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "oam:CreateLink", "oam:UpdateLink", "oam:GetLink",
      "oam:DeleteLink", "oam:GetSink", "oam:ListAttachedLinks"
    ],
    "Resource": "arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink"
  }]
}
```

### Cross-account assume role (delegated deployment)

If the source account does not run the link creation directly but
delegates to a deployment role in the monitoring account:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::111122223333:role/DeploymentRole" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": { "sts:ExternalId": "observability-fleet" }
    }
  }]
}
```

The DeploymentRole assumes the source role, creates the link as
the source account, and exits. Requires the DeploymentRole to
have `sts:AssumeRole` permission on the source role ARN.

## AMP cross-account workspace roles

AMP cross-account query uses workspace IAM roles, NOT OAM. The
workspace role trust policy determines which principals may query
or remote-write.

### Source account AMP workspace — trust policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
    "Action": "sts:AssumeRole",
    "Condition": { "StringEquals": { "aws:PrincipalTag/Role": "GrafanaAMP" } }
  }]
}
```

### Monitoring account Grafana — permission policy

The Grafana workspace role (in the monitoring account) needs
permission to assume the source account AMP role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": "arn:aws:iam::444455556666:role/AMPQueryRole"
  }]
}
```

In Grafana, add a Prometheus data source pointing at the AMP
workspace endpoint with the source account AMPQueryRole ARN.

## Full NEVER list

1. NEVER create the link from the monitoring account. The link is
   created in the SOURCE account and references the sink ARN.
2. NEVER use a wildcard sink policy without a condition. Always
   scope with `aws:PrincipalAccount`, `aws:PrincipalOrgID`, or
   explicit ARNs.
3. NEVER omit the `oam:ResourceTypes` condition on the sink
   policy when you want to restrict resource types.
4. NEVER resource-lock the source account IAM policy to
   `oam:CreateLink: *`. Scope to the specific sink ARN.
5. NEVER configure per-account Managed Grafana data sources for
   OAM-shared data. Use a single data source per Region pointing
   at the monitoring account.
6. NEVER assume OAM proxies AMP. AMP cross-account uses workspace
   role trust. Do not list AMP workspaces as an OAM resource type.
7. NEVER assume Application Signals auto-enables via OAM. Enable
   Application Signals in each source account first.
8. NEVER use uppercase or lowercase variants of namespace names.
   Filters are case-sensitive; `AWS/ECS` is canonical.
9. NEVER delete a sink without first deleting all attached links
   in the source accounts. The sink delete fails if links remain.
10. NEVER assume `prefix("...")` is a regex. It is a literal
    string prefix. `prefix("/aws/ecs/prod-")` matches log groups
    starting with that exact string; no regex metacharacters.
11. NEVER share `AWS::Logs::LogGroup` with `"*"` filter
    carelessly. This shares ALL log groups in the source account,
    potentially exposing sensitive application logs.
12. NEVER deploy a link with the same label across source accounts
    without including the account ID in the label. Duplicate
    labels confuse `list-attached-links` output in the monitoring
    account.

## Edge-case handling (extended)

### Link CREATED but not ATTACHED

The sink policy rejected the resource types in the link. Run
`aws oam get-sink-policy --sink-identifier <arn>` and verify the
`ForAllValues:StringEquals oam:ResourceTypes` condition includes
every resource type the link declared.

### Cross-account metrics missing specific namespace

The `MetricConfiguration.Filter` does not include the namespace.
Filter syntax is case-sensitive. Verify with `aws cloudwatch
list-metrics --namespace <name>` in the SOURCE account that the
namespace exists.

### Cross-account log groups empty

The `LogGroupConfiguration.Filter` does not match the actual log
group names. Use `prefix("...")` for namespace-scoped sharing.
Run `aws logs describe-log-groups` in the SOURCE account to
confirm the names.

### X-Ray service map shows source services as disconnected

The `TraceConfiguration.Filter` excludes the downstream service.
X-Ray service maps require BOTH the upstream and downstream
service in the filter. Re-include and `update-link`.

### Application Signals metrics missing in monitoring account

Application Signals is not enabled in the source account. Run
`aws application-signals list-services` in the SOURCE account. If
empty, enable Application Signals on the workload (EKS, ECS,
Lambda, EC2) using the
`cloudwatch-application-signals-deployer` skill.

### Managed Grafana queries return empty

The Grafana data source role lacks read permissions on
CloudWatch / X-Ray / OAM sink, OR the Grafana workspace Region
differs from the sink Region. Verify the role policy includes
`cloudwatch:GetMetricData`, `logs:FilterLogEvents`,
`xray:GetTraceSummaries`, `oam:GetSink`.

### AMP cross-account queries 403

The workspace role trust policy does not include the monitoring
account principal, or the tag condition is mismatched. Verify
`aws:PrincipalTag/Role` matches the tag on the Grafana role in
the monitoring account.

### Sink policy change drops existing links

Updating the sink policy to remove a source account does NOT
delete existing links but does block future updates from that
source. Delete the link in the source account first if
decommissioning.

### Cross-Region observability

OAM sinks are Region-scoped. To aggregate across Regions, create
a sink in each Region and configure Grafana with one data source
per Region. CloudWatch cross-Region metrics is a separate feature
and does not use OAM.

### Link label collisions

If two source accounts use the same link label, the monitoring
account's `list-attached-links` output is ambiguous. Include the
account ID in the label: `prod-app-link-444455556666`.

### Large fleets (> 100 source accounts)

Manual per-account sink policy entries do not scale. Use
`aws:PrincipalOrgID`. Deploy links via CloudFormation StackSets
from the monitoring account with `--permission-model
SERVICE_MANAGED` and `--auto-deployment Enabled=true`.
