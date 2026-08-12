# Drift Reporting and Athena Reference

Supplementary reference for the Drift Detection Automator skill. Use
when exporting drift reports to S3, designing Athena tables for drift
analysis, or building cross-account drift dashboards via Config
Aggregator.

## Drift report schema

The Lambda exports drift results as JSON to S3 with the following
partitioned structure:

```
s3://drift-reports-bucket/
  drift-reports/
    dt=2026-08-11/
      drift-report.json
    dt=2026-08-12/
      drift-report.json
```

Each report record has this schema:

```json
{
  "stack_name": "staging-web-app",
  "account_id": "111111111111",
  "region": "us-east-1",
  "resource_id": "sg-0abc123def",
  "resource_type": "AWS::EC2::SecurityGroup",
  "logical_resource_id": "WebServerSecurityGroup",
  "drift_status": "MODIFIED",
  "drift_severity": "CRITICAL",
  "detection_time": "2026-08-11T02:00:15Z",
  "property_path": "SecurityGroupIngress",
  "expected_value": "[{\"IpProtocol\":\"tcp\",\"FromPort\":443,...}]",
  "actual_value": "[{\"IpProtocol\":\"tcp\",\"FromPort\":22,...}]",
  "difference_type": "NOT_EQUAL",
  "suppressed": false
}
```

## Athena table creation

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS drift_reports (
  stack_name string,
  account_id string,
  region string,
  resource_id string,
  resource_type string,
  logical_resource_id string,
  drift_status string,
  drift_severity string,
  detection_time string,
  property_path string,
  expected_value string,
  actual_value string,
  difference_type string,
  suppressed boolean
)
PARTITIONED BY (dt string)
STORED AS JSON
LOCATION 's3://drift-reports-bucket/drift-reports/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2026-01-01,NOW',
  'projection.dt.format' = 'yyyy-MM-dd',
  'storage.location.template' = 's3://drift-reports-bucket/drift-reports/dt=$${dt}/'
);
```

Load partitions:

```sql
MSCK REPAIR TABLE drift_reports;
```

## Common Athena queries

### Top drifted resource types (last 7 days)

```sql
SELECT resource_type, COUNT(*) as drift_count
FROM drift_reports
WHERE dt >= date_format(current_date - interval '7' day, '%Y-%m-%d')
  AND suppressed = false
GROUP BY resource_type
ORDER BY drift_count DESC;
```

### Stacks with most frequent drift (recurring — last 30 days)

```sql
SELECT stack_name,
       COUNT(DISTINCT resource_id) as unique_drifted_resources,
       COUNT(DISTINCT dt) as drift_days
FROM drift_reports
WHERE dt >= date_format(current_date - interval '30' day, '%Y-%m-%d')
  AND suppressed = false
GROUP BY stack_name
ORDER BY unique_drifted_resources DESC, drift_days DESC;
```

### Critical drift not remediated

```sql
SELECT stack_name, resource_id, resource_type, property_path,
       expected_value, actual_value, detection_time
FROM drift_reports
WHERE drift_severity = 'CRITICAL'
  AND drift_status = 'MODIFIED'
  AND dt >= date_format(current_date - interval '7' day, '%Y-%m-%d')
ORDER BY detection_time DESC;
```

### Drift trend by day (all severities)

```sql
SELECT dt,
       drift_severity,
       COUNT(*) as count
FROM drift_reports
WHERE dt >= date_format(current_date - interval '30' day, '%Y-%m-%d')
  AND suppressed = false
GROUP BY dt, drift_severity
ORDER BY dt DESC, drift_severity;
```

### Suppressed drift audit (quarterly review)

```sql
SELECT resource_type, property_path, COUNT(*) as suppression_count
FROM drift_reports
WHERE suppressed = true
  AND dt >= date_format(current_date - interval '90' day, '%Y-%m-%d')
GROUP BY resource_type, property_path
ORDER BY suppression_count DESC;
```

### Cross-account drift summary

```sql
SELECT account_id,
       COUNT(DISTINCT stack_name) as drifted_stacks,
       COUNT(DISTINCT resource_id) as drifted_resources,
       SUM(CASE WHEN drift_severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_drifts
FROM drift_reports
WHERE dt >= date_format(current_date - interval '7' day, '%Y-%m-%d')
  AND suppressed = false
GROUP BY account_id
ORDER BY critical_drifts DESC;
```

## Config Aggregator cross-account queries

For real-time cross-account visibility without S3/Athena, use Config
Aggregator advanced queries:

```bash
# List all NON_COMPLIANT CFN stacks across aggregated accounts
aws configservice select-aggregate-resource-config \
  --configuration-aggregator-name drift-visibility-aggregator \
  --expression "SELECT resourceId, accountId, awsRegion, configurationItemStatus, complianceType
                 WHERE resourceType = 'AWS::CloudFormation::Stack'
                 AND complianceType = 'NON_COMPLIANT'"
```

```bash
# Count drifted stacks per account
aws configservice select-aggregate-resource-config \
  --configuration-aggregator-name drift-visibility-aggregator \
  --expression "SELECT accountId, COUNT(resourceId)
                 WHERE resourceType = 'AWS::CloudFormation::Stack'
                 AND complianceType = 'NON_COMPLIANT'
                 GROUP BY accountId"
```

## CloudWatch metrics for drift dashboards

Custom metrics the Lambda should emit:

| Metric name | Dimensions | Unit | Description |
|---|---|---|---|
| `DriftDetected` | StackName, Severity | Count | Number of drifted resources per detection run |
| `DriftRemediated` | StackName | Count | Number of resources remediated |
| `DriftSuppressed` | StackName | Count | Number of suppressed drift items |
| `DriftDetectionDuration` | StackName | Seconds | Time to complete drift detection |
| `DriftRemediationFailed` | StackName | Count | Failed remediation attempts |

CloudWatch alarm recommendations:

| Alarm | Threshold | Action |
|---|---|---|
| Critical drift on production stack | `DriftDetected(Severity=CRITICAL) > 0` for 1 datapoint | SNS page on-call |
| Drift not remediated for 48h | `DriftDetected > 0` for 48 consecutive hours | SNS email ops |
| Remediation failure rate | `DriftRemediationFailed / DriftDetected > 0.1` | SNS email ops |
| Detection Lambda errors | `Errors > 0` for 5 minutes | SNS email ops |

## QuickSight / Grafana dashboard panels

Recommended dashboard panels for a drift visibility dashboard:

1. **Stack-level drift heatmap** — stacks (Y) x days (X), colored by
   drift count. Reveals recurring drift patterns.
2. **Severity distribution pie** — CRITICAL/HIGH/MEDIUM/LOW over last
   7 days. Shows drift composition.
3. **Top 10 drifted resource types** — bar chart. Shows which resource
   types drift most frequently (target for IaC pipeline improvements).
4. **Cross-account drift table** — account, # drifted stacks, #
   critical drifts, last detection time. Sortable by critical count.
5. **Suppression audit table** — resource type, property, suppression
   count, last review date. For quarterly suppression review.
