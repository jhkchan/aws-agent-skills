# Cost Anomaly Monitor Types Reference

Supplementary reference for the Cost Anomaly Detection Automator skill.
Use when selecting a monitor type, designing a dimension-based monitor,
or debugging a monitor that fails to detect anomalies.

## Monitor type comparison

| `MonitorType` | `MonitorDimension` | Coverage | Best for |
|---|---|---|---|
| `DIMENSION` | `SERVICE` | All spend for one or more services | EC2, S3, RDS — high-spend services |
| `DIMENSION` | `LINKED_ACCOUNT` | All spend for one linked account | Per-member accountability in org |
| `DIMENSION` | `REGION` | Spend in a specific region | Multi-region workloads |
| `DIMENSION` | `INSTANCE_TYPE` | Spend on an instance family | GPU/spot monitoring |
| `DIMENSION` | `USAGE_TYPE` | Spend on a usage type | Granular cost driver tracking |
| `DIMENSION` | `PURCHASE_OPTION` | Spend by purchase option | RI/SP utilization tracking |
| `DIMENSION` | `SAVINGS_PLAN_ARN` | Spend against a Savings Plan | SP coverage analysis |
| `DIMENSION` | `PLATFORM` | Spend by OS platform | Linux vs Windows licensing |

## MonitorSpecification JSON structure

The `MonitorSpecification` is a JSON-encoded `Expression` object (same
as Cost Explorer `Filter`). It supports `Dimensions`, `Tags`, `CostCategories`,
and `And`/`Or`/`Not` combinators.

### Single-dimension monitor (most common)

```json
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": ["Amazon Elastic Compute Cloud - Compute"],
    "MatchOptions": ["EQUALS"]
  }
}
```

### Multi-value dimension monitor

```json
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": [
      "Amazon Elastic Compute Cloud - Compute",
      "Amazon Simple Storage Service"
    ],
    "MatchOptions": ["EQUALS"]
  }
}
```

### All-services monitor (broadest detection)

```json
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": [],
    "MatchOptions": ["EQUALS"]
  }
}
```

### Linked-account monitor

```json
{
  "Dimensions": {
    "Key": "LINKED_ACCOUNT",
    "Values": ["222222222222"],
    "MatchOptions": ["EQUALS"]
  }
}
```

## MatchOptions reference

| MatchOption | Behavior |
|---|---|
| `EQUALS` | Exact string match on dimension value |
| `STARTS_WITH` | Prefix match (e.g., `"Amazon"` matches all Amazon services) |
| `ENDS_WITH` | Suffix match |
| `CONTAINS` | Substring match |
| `CASE_SENSITIVE` | Modifier — combine with above for case-sensitive matching |
| `CASE_INSENSITIVE` | Modifier — default behavior |

## Common pitfalls

### Wrong service name

The `SERVICE` dimension uses the full display name from the AWS Cost
Explorer, NOT the short API name. For example:
- Correct: `"Amazon Elastic Compute Cloud - Compute"`
- Wrong: `"EC2"`, `"ec2"`, `"Amazon EC2"`

Always verify the exact service name via:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-11 \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[].Keys[0]'
```

### Empty Values array

A monitor with `"Values": []` for `SERVICE` detects anomalies across
ALL services. This is the broadest detection but produces org-wide
alerts that require routing logic. For targeted monitoring, always
specify the service name(s).

### Dimension not in billing data

A monitor referencing a `LINKED_ACCOUNT` that has no spend in the
trailing 10+ days will never detect anomalies. Verify the account has
billable activity before creating the monitor.

## Monitor lifecycle

| State | Meaning | Operator action |
|---|---|---|
| `PENDING` | Provisioning in progress | Wait; poll `get-anomaly-monitors` |
| `ACTIVE` | Detecting anomalies | Safe to create subscriptions |
| `INACTIVE` | Disabled | Re-enable or delete and recreate |
| `DELETED` | Removed | Cannot be recovered; recreate if needed |

A subscription created against a `PENDING` monitor does NOT error but
silently fails to deliver alerts until the monitor transitions to
`ACTIVE`. Always verify `monitorStatus` is `ACTIVE` before wiring
subscriptions.

## Verification queries

### Confirm monitor is ACTIVE

```bash
aws ce get-anomaly-monitors \
  --query 'AnomalyMonitors[?MonitorName==`ec2-spend-anomaly-monitor`].[MonitorName,MonitorType,MonitorDimension,MonitorStatus]'
```

### List all existing monitors

```bash
aws ce get-anomaly-monitors \
  --query 'AnomalyMonitors[].[MonitorName,MonitorType,MonitorStatus]' \
  --output table
```

### Delete a monitor (irreversible)

```bash
aws ce delete-anomaly-monitor \
  --monitor-arn "<monitor-arn>"
```

All subscriptions for the monitor are also deleted. Back up the monitor
configuration before deleting.

---

## Appendix A — Monitor type comparison (moved from SKILL.md)

| Monitor type | `MonitorDimension` | Coverage | Best for |
|---|---|---|---|
| Service-level | `SERVICE` | All spend for a specific service | EC2, S3, RDS — high-spend services |
| Linked-account | `LINKED_ACCOUNT` | All spend for one account | Per-member accountability in org |
| Region-based | `REGION` | Spend in a specific region | Multi-region workloads |
| Instance-type | `INSTANCE_TYPE` | Spend on a specific instance family | GPU/spot instance monitoring |
| All-services | `SERVICE` (all values) | All services | Broadest ML-based detection |
