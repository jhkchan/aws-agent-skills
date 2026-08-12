# CloudWatch Dashboard JSON Templates Reference

Load this reference when creating or updating CloudWatch dashboards. The
templates below cover the standard service dashboards (RDS, EC2, Lambda,
ECS) with complete JSON models ready for PutDashboard API.

## Dashboard JSON structure

Every dashboard body follows this top-level structure:

```json
{
  "widgets": [
    {
      "type": "metric | log | alarm | custom | text",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Widget Title",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average | Sum | Maximum | Minimum | SampleCount",
        "view": "timeSeries | singleValue | table | bar | pie | heatmap",
        "metrics": [],
        "query": "",
        "annotations": {},
        "liveData": false,
        "setPeriodToTimeRange": true,
        "trend": false,
        "stacked": false,
        "legend": { "position": "bottom" }
      }
    }
  ]
}
```

## Widget coordinate system

- Grid: 24 columns wide, unlimited rows.
- `x`: 0-23 (horizontal position).
- `y`: 0+ (vertical position, increments by widget height).
- `width`: typically 6, 12, or 24.
- `height`: typically 3, 6, or 8.

## RDS monitoring dashboard template

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "CPU Utilization (%)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${DBInstance}", {"label": "CPU %"}]
        ],
        "annotations": {
          "horizontal": [{"label": "Alarm threshold", "value": 80, "fill": "above"}]
        }
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Database Connections",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", "${DBInstance}", {"id": "m1"}],
          [{"expression": "m1", "label": "Active Connections", "id": "e1"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Freeable Memory (MB)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "FreeableMemory", "DBInstanceIdentifier", "${DBInstance}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Free Storage Space (GB)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", "${DBInstance}", {"id": "m1"}],
          [{"expression": "m1 / 1073741824", "label": "Free Storage (GB)", "id": "e1"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 12, "width": 12, "height": 6,
      "properties": {
        "title": "Read/Write IOPS",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "ReadIOPS", "DBInstanceIdentifier", "${DBInstance}", {"label": "Read IOPS"}],
          ["AWS/RDS", "WriteIOPS", "DBInstanceIdentifier", "${DBInstance}", {"label": "Write IOPS"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 12, "width": 12, "height": 6,
      "properties": {
        "title": "Query Throughput (queries/sec)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "Queries", "DBInstanceIdentifier", "${DBInstance}"],
          ["AWS/RDS", "SelectQueries", "DBInstanceIdentifier", "${DBInstance}"],
          ["AWS/RDS", "InsertQueries", "DBInstanceIdentifier", "${DBInstance}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 18, "width": 12, "height": 6,
      "properties": {
        "title": "Replica Lag (seconds)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Maximum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/RDS", "ReplicaLag", "DBInstanceIdentifier", "${DBInstance}"]
        ]
      }
    },
    {
      "type": "alarm",
      "x": 12, "y": 18, "width": 12, "height": 6,
      "properties": {
        "title": "RDS Alarms",
        "region": "us-east-1",
        "alarms": ["arn:aws:cloudwatch:us-east-1:111111111111:alarm:rds-cpu-high"]
      }
    }
  ]
}
```

## EC2 monitoring dashboard template

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 24, "height": 6,
      "properties": {
        "title": "Top 10 EC2 Instances by CPU (Metrics Insights)",
        "region": "us-east-1",
        "view": "table",
        "query": "SELECT avg(CPUUtilization) FROM AWS/EC2 GROUP BY InstanceId ORDER BY avg() DESC LIMIT 10"
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Network In/Out (bytes)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/EC2", "NetworkIn", "InstanceId", "${InstanceId}"],
          ["AWS/EC2", "NetworkOut", "InstanceId", "${InstanceId}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Status Checks",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/EC2", "StatusCheckFailed", "InstanceId", "${InstanceId}"],
          ["AWS/EC2", "StatusCheckFailed_Instance", "InstanceId", "${InstanceId}"],
          ["AWS/EC2", "StatusCheckFailed_System", "InstanceId", "${InstanceId}"]
        ]
      }
    }
  ]
}
```

## Lambda monitoring dashboard template

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Invocations & Errors",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Invocations", "FunctionName", "${FunctionName}", {"id": "m1"}],
          ["AWS/Lambda", "Errors", "FunctionName", "${FunctionName}", {"id": "m2"}],
          [{"expression": "m2 / m1 * 100", "label": "Error Rate (%)", "id": "e1", "yAxis": "right"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Duration (ms) - p50, p95, p99",
        "region": "us-east-1",
        "period": 300,
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "${FunctionName}", {"stat": "p50"}],
          ["AWS/Lambda", "Duration", "FunctionName", "${FunctionName}", {"stat": "p95"}],
          ["AWS/Lambda", "Duration", "FunctionName", "${FunctionName}", {"stat": "p99"}]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Throttles & ConcurrentExecutions",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Throttles", "FunctionName", "${FunctionName}"],
          ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${FunctionName}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Errors - Anomaly Detection",
        "region": "us-east-1",
        "period": 300,
        "stat": "Sum",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Errors", "FunctionName", "${FunctionName}", {"id": "m1"}],
          [{"expression": "ANOMALY_DETECTION_BAND(m1, 2)", "label": "Expected Band", "id": "ad1"}]
        ]
      }
    }
  ]
}
```

## ECS monitoring dashboard template

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "CPU Utilization (%)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/ECS", "CPUUtilization", "ClusterName", "${ClusterName}", "ServiceName", "${ServiceName}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 12, "y": 0, "width": 12, "height": 6,
      "properties": {
        "title": "Memory Utilization (%)",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/ECS", "MemoryUtilization", "ClusterName", "${ClusterName}", "ServiceName", "${ServiceName}"]
        ]
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 6, "width": 12, "height": 6,
      "properties": {
        "title": "Running & Pending Tasks",
        "region": "us-east-1",
        "period": 300,
        "stat": "Average",
        "view": "timeSeries",
        "metrics": [
          ["AWS/ECS", "RunningTaskCount", "ClusterName", "${ClusterName}", "ServiceName", "${ServiceName}"],
          ["AWS/ECS", "PendingTaskCount", "ClusterName", "${ClusterName}", "ServiceName", "${ServiceName}"]
        ]
      }
    }
  ]
}
```

## Metrics Insights query syntax

```sql
-- Top 10 EC2 instances by CPU
SELECT avg(CPUUtilization)
FROM AWS/EC2
WHERE AutoScalingGroupName LIKE 'prod-%'
GROUP BY InstanceId
ORDER BY avg() DESC
LIMIT 10

-- Average latency by Lambda function
SELECT avg(Duration)
FROM AWS/Lambda
GROUP BY FunctionName
ORDER BY avg() DESC
LIMIT 20

-- Cross-account RDS CPU (requires OAM)
SELECT avg(CPUUtilization)
FROM AWS/RDS
GROUP BY @Account, DBInstanceIdentifier
ORDER BY avg() DESC
LIMIT 20
```

## Custom widget (Lambda-backed)

```json
{
  "type": "custom",
  "x": 0, "y": 0, "width": 24, "height": 6,
  "properties": {
    "title": "Custom Widget - Lambda Function",
    "endpoint": "arn:aws:lambda:us-east-1:111111111111:function:custom-dashboard-widget",
    "updateOn": {"refresh": true, "resize": true, "timeRange": true},
    "title": "Custom Metric Table"
  }
}
```

The Lambda function receives the dashboard context (time range,
variables, widget dimensions) and returns HTML that renders in the
widget. The Lambda must have a resource-based policy allowing
`cloudwatch.amazonaws.com` to invoke it.
