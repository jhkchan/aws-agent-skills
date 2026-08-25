# Athena partition projection and CUR query patterns

Reference loaded on demand when the skill needs the exact partition
projection syntax or one of the standard CUR queries.

## Partition projection — full TBLPROPERTIES block

```sql
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.year.type' = 'integer',
  'projection.year.range' = '2024,2999',
  'projection.year.digits' = '4',
  'projection.month.type' = 'date',
  'projection.month.range' = '2024/01,NOW',
  'projection.month.format' = 'yyyy/MM',
  'projection.day.type' = 'date',
  'projection.day.range' = '2024/01/01,NOW',
  'projection.day.format' = 'yyyy/MM/dd',
  'projection.day.interval' = '1',
  'projection.day.interval.unit' = 'DAYS',
  'storage.location.template' = 's3://<CUR_BUCKET>/<CUR_PREFIX>/year=${year}/month=${month}/day=${day}'
)
```

Notes:
- `projection.day.range = '2024/01/01,NOW'` — the literal `NOW` is
  evaluated by Athena at query time. Requires Athena engine version 3.
- `storage.location.template` MUST use `${var}` (not `$var`) — Athena
  substitutes partition values into the template.
- The CUR prefix must match exactly what CUR writes — `cur/<report-name>/`
  is the AWS convention.

## Standard CUR named queries

### top_spenders_by_service (current month)

```sql
SELECT product_servicename AS service,
       SUM(lineitem_unblendedcost) AS cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_trunc('month', current_date), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
  AND lineitem_lineitemtype IN ('Usage', 'DiscountedUsage', 'SavingsPlanCoveredUsage')
GROUP BY product_servicename
ORDER BY cost DESC
LIMIT 20;
```

### top_spenders_by_linked_account

```sql
SELECT lineitem_usageaccountid AS account_id,
       SUM(lineitem_unblendedcost) AS cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_trunc('month', current_date), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
GROUP BY lineitem_usageaccountid
ORDER BY cost DESC;
```

### unused_ec2_resources (joined with CloudWatch metrics)

```sql
WITH ec2_cost AS (
  SELECT lineitem_resourceid AS instance_id,
         SUM(lineitem_unblendedcost) AS cost
  FROM cur_hourly
  WHERE day BETWEEN date_format(date_sub(current_date, 30), 'yyyy/MM/dd')
                AND date_format(current_date, 'yyyy/MM/dd')
    AND lineitem_productcode = 'AmazonEC2'
    AND lineitem_usagetype LIKE '%BoxUsage%'
  GROUP BY lineitem_resourceid
),
cw_network AS (
  SELECT instance_id, MAX(network_in) AS max_net_in
  FROM cloudwatch_metrics_ec2  -- external Athena data source connector
  WHERE day >= date_sub(current_date, 30)
  GROUP BY instance_id
)
SELECT c.instance_id, c.cost, n.max_net_in
FROM ec2_cost c
LEFT JOIN cw_network n ON c.instance_id = n.instance_id
WHERE n.max_net_in IS NULL OR n.max_net_in = 0
ORDER BY c.cost DESC;
```

### savings_plan_opportunities (on-demand spend eligible for SP)

```sql
SELECT lineitem_productcode AS service,
       lineitem_usagetype AS usage_type,
         product_instancetype AS instance_type,
         product_region AS region,
         SUM(lineitem_unblendedcost) AS on_demand_cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_sub(current_date, 30), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
  AND lineitem_lineitemtype = 'Usage'
  AND pricing_term = 'OnDemand'
  AND lineitem_productcode IN ('AmazonEC2', 'AmazonECS', 'AmazonEKS', 'Lambda', 'AmazonFSx', 'AmazonRDS', 'AmazonRedshift')
GROUP BY 1, 2, 3, 4
HAVING SUM(lineitem_unblendedcost) > 100
ORDER BY on_demand_cost DESC;
```

### ri_utilization (Reserved Instance coverage)

```sql
SELECT lineitem_productcode AS service,
       lineitem_usagetype AS usage_type,
         product_region AS region,
         SUM(CASE WHEN lineitem_lineitemtype = 'DiscountedUsage'
                  THEN lineitem_unblendedcost ELSE 0 END) AS discounted_cost,
         SUM(CASE WHEN lineitem_lineitemtype = 'RIFee'
                  THEN lineitem_unblendedcost ELSE 0 END) AS ri_fee,
         SUM(CASE WHEN lineitem_lineitemtype = 'UnusedReservation'
                  THEN lineitem_unblendedcost ELSE 0 END) AS unused_ri,
         SUM(lineitem_unblendedcost) AS total_cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_trunc('month', current_date), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
  AND lineitem_lineitemtype IN ('Usage', 'DiscountedUsage', 'RIFee', 'UnusedReservation')
  AND pricing_term = 'Reserved'
GROUP BY 1, 2, 3
ORDER BY total_cost DESC;
```

### tag_compliance_gaps

```sql
SELECT lineitem_productcode AS service,
       lineitem_resourceid AS resource_id,
         SUM(lineitem_unblendedcost) AS cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_sub(current_date, 7), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
  AND resource_tags_user_env IS NULL
GROUP BY 1, 2
HAVING SUM(lineitem_unblendedcost) > 50
ORDER BY cost DESC;
```

### eks_pod_cost_attribution (requires CUR 2.0 SCAD)

```sql
SELECT split_cost_allocation_data_resource AS pod_name,
       split_cost_allocation_data_usage AS usage_metric,
         SUM(lineitem_unblendedcost) AS cost
FROM cur_hourly
WHERE day BETWEEN date_format(date_sub(current_date, 7), 'yyyy/MM/dd')
              AND date_format(current_date, 'yyyy/MM/dd')
  AND lineitem_productcode = 'AmazonEKS'
  AND split_cost_allocation_data_resource IS NOT NULL
GROUP BY 1, 2
ORDER BY cost DESC
LIMIT 50;
```

## Query automation via EventBridge Scheduler + Lambda

```yaml
EventBridgeSchedule:
  Type: AWS::Scheduler::Schedule
  Properties:
    Name: cur-top-spenders-daily
    ScheduleExpression: cron(0 14 * * ? *)  # 9am ET
    FlexibleTimeWindow:
      Mode: "OFF"
    Target:
      Arn: !GetAtt TopSpendersLambda.Arn
      RoleArn: !GetAtt SchedulerRole.Arn

TopSpendersLambda:
  Type: AWS::Lambda::Function
  Properties:
    Runtime: python3.12
    Handler: index.lambda_handler
    Environment:
      Variables:
        WORKGROUP: finops-cur
        DATABASE: prod_cur
        SLACK_WEBHOOK_URL: !Ref SlackWebhookUrl
    Code:
      ZipFile: |
        import boto3, json, urllib3, os
        athena = boto3.client('athena')
        def lambda_handler(event, context):
            query = """
              SELECT product_servicename, SUM(lineitem_unblendedcost) AS cost
              FROM cur_hourly
              WHERE day BETWEEN date_format(date_trunc('month', current_date), 'yyyy/MM/dd')
                            AND date_format(current_date, 'yyyy/MM/dd')
              GROUP BY product_servicename
              ORDER BY cost DESC LIMIT 10;
            """
            res = athena.start_query_execution(
                QueryString=query,
                WorkGroup=os.environ['WORKGROUP'],
                QueryExecutionContext={'Database': os.environ['DATABASE']}
            )
            exec_id = res['QueryExecutionId']
            # ... poll for completion, format Slack message, POST
```

## Athena workgroup DSL configuration

```yaml
WorkGroupConfiguration:
  EnforceWorkgroupConfiguration: true
  BytesScannedCutoffPerQuery: 1099511627776  # 1 TB
  ResultConfiguration:
    OutputLocation: !Sub "s3://${AthenaResultsBucket}/queries/"
    EncryptionConfiguration:
      EncryptionOption: SSE_KMS
      KmsKey: !Ref AthenaKeyArn
  EngineVersion:
    SelectedEngineVersion: Athena engine version 3
```

Why these defaults:
- **EnforceWorkgroupConfiguration: true** — clients cannot override the
  DSL. Without enforcement, the byte cutoff is advisory.
- **1 TB cutoff** — caps a single query at ~$5 ($5/TB). The largest
  legitimate monthly top-spenders query scans ~50 GB.
- **Athena engine version 3** — required for partition projection with
  `NOW` as the range end.

## Patterns — IaC templates: non-negotiable TBLPROPERTIES and workgroup blocks

Full CloudFormation and Terraform templates (CUR definition + Glue DB +
Glue Table with partition projection + non-primary workgroup with DSL +
named queries) live in `references/athena-partition-projection-and-queries.md`.

The non-negotiable TBLPROPERTIES block for partition projection:

```text
projection.enabled = true
projection.day.type = date
projection.day.range = "2024/01/01,NOW"  # literal NOW, Athena engine v3
projection.day.format = "yyyy/MM/dd"
projection.day.interval = 1
projection.day.interval.unit = DAYS
storage.location.template = s3://<bucket>/<prefix>/year=${year}/month=${month}/day=${day}
```

The non-negotiable workgroup configuration:

```text
EnforceWorkgroupConfiguration = true
BytesScannedCutoffPerQuery = 1099511627776  # 1 TB cutoff
EngineVersion = Athena engine version 3  # required for NOW range end
```
