# Health Check & ARC Procedures — Route 53 Routing Policy Deployer

Reference procedures for health check creation, calculated/inverted
health checks, traffic policy instance update, and ARC safety-rule +
readiness-check configuration. Stored here so the main skill body
stays scannable.

## 1. Standard HTTPS health check with string matching

```bash
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '
    Type=HTTPS,
    Port=443,
    ResourcePath=/healthz,
    FullyQualifiedDomainName=api.example.com,
    RequestInterval=30,
    FailureThreshold=3,
    EnableSNI=true,
    MatchThreshold=90,
    MatchString="ok",
    MeasureLatency=true,
    Regions="[\"us-east-1\",\"us-west-2\",\"eu-west-1\"]"
  '
```

- `FailureThreshold: 3` with `RequestInterval: 30` = 90s from failure
  onset to HC unhealthy. Tune to your tolerance.
- `EnableSNI: true` is mandatory for most modern TLS endpoints.
- `MatchString` performs a substring match in the response body. For
  regex, use `MatchRegex`. `MatchThreshold` is the percentage of
  checkers that must observe the match (use 100 for strict, 90 for
  lenient multi-region).
- `Regions` should include the regions closest to your users; Route 53
  averages across them.

## 2. Calculated health check (AND/OR of children)

For a DR decision that combines multiple signals:

```bash
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '
    Type=CALCULATED,
    HealthThreshold=2,
    ChildHealthChecks="[\"hc-aaa\",\"hc-bbb\",\"hc-ccc\"]"
  '
```

- `HealthThreshold: 2` of 3 children must be healthy for the
  calculated HC to be healthy (majority).
- For strict AND, set `HealthThreshold = len(children)`.
- For OR, set `HealthThreshold = 1`.

## 3. Inverted child health check

For "healthy when the failover endpoint is DOWN" (used by some
failover-over-pending patterns):

```bash
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '
    Type=HTTPS,
    Port=443,
    ResourcePath=/secondary-healthz,
    FullyQualifiedDomainName=secondary.example.com,
    RequestInterval=30,
    FailureThreshold=3,
    Inverted=true
  '
```

`Inverted: true` flips the result — the HC reports Healthy when the
endpoint is unreachable. Useful for "secondary should be queried
only when primary is down" patterns combined with a calculated HC.

## 4. CloudWatch-alarm health check (for private endpoints)

For endpoints Route 53's public checkers cannot reach:

```bash
aws route53 create-health-check \
  --caller-reference "$(date +%s)" \
  --health-check-config '
    Type=CLOUDWATCH_METRIC,
    AlarmIdentifier.Region=us-east-1,
    AlarmIdentifier.Name=internal-api-health
  '
```

The CloudWatch alarm is updated by a Lambda or a custom metric that
checks the private endpoint from inside the VPC. This is the only way
to health-check a private-VPC endpoint.

## 5. Traffic policy instance update (version bump)

After updating the policy document (which creates a new version), move
the instance to the new version:

```bash
aws route53 update-traffic-policy-instance \
  --id <INSTANCE_ID> \
  --ttl 60 \
  --traffic-policy-id <POLICY_ID> \
  --traffic-policy-version <NEW_VERSION>
```

Without this call, the instance continues resolving per the old
version. The new version is created but unused — a common silent-
failure mode.

## 6. ARC safety rule (ASSERTION type)

The mandatory safety rule that blocks "all controls off":

```bash
aws route53-recovery-control-config create-safety-rule \
  --control-panel-arn <PANEL_ARN> \
  --name prevent-all-off \
  --safety-rule-type ASSERTION \
  --asserted-controls "[\"<CONTROL_ARN_USE1>\",\"<CONTROL_ARN_USW2>\"]" \
  --wait-period-minutes 1 \
  --rule-config '{
    "Type": "ASSERTION",
    " assertions": [{
      "Assert": "control(\\\"<CONTROL_ARN_USE1>\\\") || control(\\\"<CONTROL_ARN_USW2>\\\")",
      "AssertedControls": ["<CONTROL_ARN_USE1>", "<CONTROL_ARN_USW2>"]
    }]
  }'
```

The rule logic: "at least one of the regional routing controls must be
ON." Flipping both OFF is blocked by ARC.

## 7. ARC readiness check

The pre-cutover gate that confirms the standby has capacity:

```bash
aws route53-recovery-readiness create-resource-set \
  --resource-set-name api-resources \
  --resource-set-type Route53RecoveryReadiness.AWS::ApiGatewayV2::Stage \
  --resources '[{
    "ResourceArn": "arn:aws:apigateway:us-west-2::/apis/<id>/stages/prod",
    "ReadinessScopes": ["<RESOURCE_SET_ARN>"]
  }]'

aws route53-recovery-readiness create-readiness-check \
  --readiness-check-name api-failover \
  --resource-set-arn <RESOURCE_SET_ARN>
```

Before any cutover, call `get-readiness-check` and confirm
`ReadinessStatus: READY`. Cutover without readiness = overload risk.

## 8. Verifying with `test-dns-answer`

The single most useful verification command:

```bash
aws route53 test-dns-answer \
  --hosted-zone-id <ZONE_ID> \
  --record-name api.example.com. \
  --record-type A \
  --resolver 8.8.8.8 \
  --edns0-client-subnet-ip 203.0.113.10/32
```

For geo / IP-based routing, supply `--edns0-client-subnet-ip` to test
how a client from a specific IP would be routed. Without it, Route 53
returns the record matching the resolver's IP — which may not match
your user's location.

## 9. ARC routing-control flip (the actual cutover)

This is an EXECUTE step, not a deploy step — but the deployer skill
must document it because it is the operational result of an ARC
deployment:

```bash
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn <CONTROL_ARN_USE1> \
  --routing-control-state On

aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn <CONTROL_ARN_USW2> \
  --routing-control-state Off
```

Both flips happen in the same call sequence; the safety rule prevents
both being OFF simultaneously. For the execute-time procedure (with
readiness pre-check and alarm acknowledgment), use the
route53-failover-operator skill.

## Step 6 — Traffic policy / ARC routing control CLIs

#### 6a. Traffic policy (visual-editor, versioned routing-as-code)

```bash
aws route53 create-traffic-policy \
  --name <POLICY_NAME> \
  --document file://policy.json
```

The policy document encodes the routing graph (start record, endpoints,
rules). To deploy, create an instance:

```bash
aws route53 create-traffic-policy-instance \
  --hosted-zone-id <ZONE_ID> \
  --name api.example.com. \
  --ttl 60 \
  --traffic-policy-id <POLICY_ID> \
  --traffic-policy-version 1
```

**Common mistake:** updating the policy document creates a new version,
but the existing instance continues pointing at version 1 until you
explicitly `update-traffic-policy-instance`. The change looks like it
did nothing.

#### 6b. Application Recovery Controller

```bash
# Cluster + control panel (one-time)
aws route53-recovery-control-config create-cluster --cluster-name <NAME>
aws route53-recovery-control-config create-control-panel \
  --cluster-arn <CLUSTER_ARN> --control-panel-name <NAME>

# Routing control
aws route53-recovery-control-config create-routing-control \
  --cluster-arn <CLUSTER_ARN> \
  --control-panel-arn <PANEL_ARN> \
  --routing-control-name us-east-1-routing

# Safety rule (MANDATORY)
aws route53-recovery-control-config create-safety-rule \
  --control-panel-arn <PANEL_ARN> \
  --safety-rule-type ASSERTION \
  --asserted-controls <CONTROL_ARN_1>,<CONTROL_ARN_2> \
  --name prevent-all-off

# Readiness check
aws route53-recovery-readiness create-readiness-check \
  --readiness-check-name <NAME> \
  --resource-set-arn <RESOURCE_SET_ARN>
```
