# IAM Policies and Magnetic Store Writes — Timestream Database Deployer

Deep reference on IAM policy structure for Timestream resource types
(database, table, scheduled query, batch load task), the magnetic
store write S3 bucket policy requirement, and the scheduled query
execution role permissions. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays
scannable.

## Timestream resource types and ARN patterns

| Resource type | ARN pattern |
|---|---|
| Database | `arn:aws:timestream:<region>:<account>:database/<database-name>` |
| Table | `arn:aws:timestream:<region>:<account>:database/<database-name>/table/<table-name>` |
| Scheduled query | `arn:aws:timestream:<region>:<account>:scheduled-query/<query-name>` |
| Batch load task | `arn:aws:timestream:<region>:<account>:batch-load-task/<task-id>` |

## IAM policy for full table access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:WriteRecords",
        "timestream:DescribeTable",
        "timestream:UpdateTable",
        "timestream:DeleteTable"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData/table/TemperatureReadings"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeDatabase",
        "timestream:ListTables"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData"
      ]
    }
  ]
}
```

**Critical:** the `timestream:DescribeEndpoints` action is required for
ALL Timestream operations. It uses `Resource: "*"` because it returns
the service endpoint addresses (Timestream uses regional endpoints
dynamically).

## IAM policy for query access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:Select",
        "timestream:DescribeTable",
        "timestream:DescribeDatabase"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData",
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData/table/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:CancelQuery"
      ],
      "Resource": "*"
    }
  ]
}
```

## Scheduled query execution role

The scheduled query execution role requires three categories of
permissions:

1. **Query the source table** — `timestream:Select` on the source
   table ARN.
2. **Write to the target table** — `timestream:WriteRecords` on the
   target table ARN.
3. **Publish error notifications** — `sns:Publish` on the SNS topic
   ARN.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:Select",
        "timestream:DescribeTable"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData/table/TemperatureReadings"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:WriteRecords"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/IoTSensorData/table/HourlyTempAggregates"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": [
        "arn:aws:sns:us-east-1:123456789012:timestream-scheduled-query-errors"
      ]
    }
  ]
}
```

**Trust policy for the execution role:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "timestream.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Magnetic store write S3 bucket policy

When magnetic store write properties are enabled, Timestream writes
late-arrival data to an S3 bucket. The bucket must have a policy
granting `s3:PutObject` to the Timestream service principal.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "timestream.amazonaws.com"
      },
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::timestream-magnetic-late-arrival-us-east-1/*"
    }
  ]
}
```

### Verifying the bucket policy

```bash
# Check the bucket policy
aws s3api get-bucket-policy \
  --bucket timestream-magnetic-late-arrival-us-east-1 \
  --region us-east-1

# Verify the table's magnetic store write properties
aws timestream-write describe-table \
  --database-name IoTSensorData \
  --table-name TemperatureReadings \
  --query 'Table.MagneticStoreWriteProperties' \
  --region us-east-1
```

### Common bucket policy mistakes

- **Missing `s3:PutObject` permission** — the bucket policy grants
  `s3:GetObject` or `s3:ListBucket` but not `s3:PutObject`. Timestream
  cannot write late-arrival data.

- **Wrong principal** — the policy uses an IAM role ARN instead of the
  Timestream service principal (`timestream.amazonaws.com`).

- **Cross-region bucket** — the S3 bucket is in a different region
  than the Timestream table. Timestream requires the bucket to be in
  the same region.

- **Resource path too narrow** — the policy only grants access to a
  specific prefix, but Timestream writes to a managed prefix
  structure. Use `/*` to cover all objects.

## Batch load task IAM role

The batch load task requires an IAM role with permissions to read
from the data source S3 bucket and write to the Timestream table.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::historical-sensor-data",
        "arn:aws:s3:::historical-sensor-data/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::batch-load-reports/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "timestream:WriteRecords"
      ],
      "Resource": [
        "arn:aws:timestream:us-east-1:123456789012:database/HistoricalData/table/SensorArchive"
      ]
    }
  ]
}
```
