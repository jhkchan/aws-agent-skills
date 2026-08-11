# CLI Commands and IaC — Kinesis Data Analytics Deployer

Full copy-pasteable CLI command sequence for all 11 deployment steps.
Variables to substitute: `<region>`, `<account-id>`, `<app-name>`,
`<runtime-env>`, `<exec-role>`, `<source-stream-arn>`,
`<destination-stream-arn>`, `<log-group>`, `<code-bucket>`,
`<code-key>`, `<checkpoint-interval>`, `<parallelism>`,
`<parallelism-per-kpu>`, `<vpc-subnet-ids>`, `<security-group-ids>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm execution role trust policy
aws iam get-role --role-name <exec-role> \
  --query 'Role.AssumeRolePolicyDocument'

# Confirm source Kinesis stream exists and is ACTIVE
aws kinesis describe-stream --stream-name <source-stream-name> \
  --query 'StreamDescription.{Status:StreamStatus,Shards:Shards[*].ShardId}'

# Confirm destination Kinesis stream exists (if Kinesis destination)
aws kinesis describe-stream --stream-name <destination-stream-name> \
  --query 'StreamDescription.{Status:StreamStatus}'

# Confirm Firehose delivery stream exists (if Firehose destination)
aws firehose describe-delivery-stream --delivery-stream-name <delivery-stream-name> \
  --query 'DeliveryStreamDescription.DeliveryStreamStatus'

# Confirm S3 code object exists (Flink apps)
aws s3 ls s3://<code-bucket>/<code-key> 2>/dev/null || echo "Code object not found"

# Confirm VPC subnets exist (if private sources like MSK)
aws ec2 describe-subnets --subnet-ids <vpc-subnet-ids> \
  --query 'Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,Type:MapPublicIpOnLaunch}'

# Confirm service quota for KPUs
aws service-quotas get-service-quota \
  --service-code kinesisanalytics \
  --quota-code L-XXXXXXXX \
  --query 'Quota.Value'

# Confirm CloudWatch log group exists
aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/

# Confirm Glue schema registry (if Avro/Protobuf)
aws glue get-registry --registry-name <registry-name> 2>/dev/null || echo "Registry not found"
```

## Step 1: IAM service execution role

```bash
aws iam create-role \
  --role-name <exec-role> \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "kinesisanalytics.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <exec-role> \
  --policy-name kda-exec \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["kinesis:GetRecords", "kinesis:GetShardIterator", "kinesis:DescribeStreamSummary", "kinesis:ListShards"],
        "Resource": "<source-stream-arn>"
      },
      {
        "Effect": "Allow",
        "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
        "Resource": "<destination-stream-arn>"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": "arn:aws:s3:::<code-bucket>/<code-key>"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"],
        "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/kinesis-analytics/*"
      },
      {
        "Effect": "Allow",
        "Action": ["kinesisanalytics:CreateApplicationSnapshot", "kinesisanalytics:DeleteApplicationSnapshot", "kinesisanalytics:DescribeApplicationSnapshot"],
        "Resource": "arn:aws:kinesisanalytics:<region>:<account-id>:application/<app-name>"
      }
    ]
  }'
```

For VPC access (private MSK or OpenSearch), add:

```json
{
  "Effect": "Allow",
  "Action": ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DeleteNetworkInterface"],
  "Resource": "*"
}
```

## Step 2: Confirm source stream

```bash
aws kinesis describe-stream --stream-name <source-stream-name> \
  --query 'StreamDescription.{Status:StreamStatus,ARN:StreamARN,Shards:Shards[*].ShardId}'
# StreamStatus MUST be ACTIVE
```

## Step 3: Create the Flink application

```bash
aws kinesisanalyticsv2 create-application \
  --application-name <app-name> \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::<account-id>:role/<exec-role> \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::<code-bucket>",
          "FileKey": "<code-key>"
        },
        "CodeContentType": "ZIPFILE"
      },
      "CodeContentType": "ZIPFILE"
    },
    "FlinkApplicationConfiguration": {
      "CheckpointConfiguration": {
        "ConfigurationType": "CUSTOM",
        "CheckpointingEnabled": true,
        "CheckpointInterval": <checkpoint-interval>,
        "MinPauseBetweenCheckpoints": 5000
      },
      "ParallelismConfiguration": {
        "ConfigurationType": "CUSTOM",
        "Parallelism": <parallelism>,
        "ParallelismPerKPU": <parallelism-per-kpu>
      },
      "MonitoringConfiguration": {
        "ConfigurationType": "CUSTOM",
        "MetricsLevel": "APPLICATION",
        "LogLevel": "INFO",
        "LogStreamARN": "arn:aws:logs:<region>:<account-id>:log-group:<log-group>"
      }
    },
    "EnvironmentProperties": {
      "PropertyGroups": [
        {"PropertyGroupId": "ConsumerConfig", "PropertyMap": {"STREAM_NAME": "<source-stream-name>", "AWS_REGION": "<region>", "SCAN_START_POSITION": "LATEST"}}
      ]
    },
    "ApplicationSnapshotConfiguration": {
      "SnapshotsEnabled": true
    }
  }' \
  --tags Environment=production,Application=<app-name>
```

## Step 4: Create the SQL application

```bash
aws kinesisanalyticsv2 create-application \
  --application-name <app-name> \
  --runtime-environment SQL-1_0 \
  --service-execution-role arn:aws:iam::<account-id>:role/<exec-role> \
  --application-configuration '{
    "SqlApplicationConfiguration": {
      "Inputs": [{
        "NamePrefix": "SOURCE_SQL_STREAM",
        "KinesisStreamsInput": {
          "ResourceARN": "<source-stream-arn>",
          "RoleARN": "arn:aws:iam::<account-id>:role/<exec-role>"
        },
        "InputSchema": {
          "RecordFormat": {"RecordFormatType": "JSON"},
          "RecordColumns": [
            {"Name": "event_time", "SqlType": "TIMESTAMP", "Mapping": "$.event_time"},
            {"Name": "user_id", "SqlType": "VARCHAR(64)", "Mapping": "$.user_id"}
          ]
        },
        "InputParallelism": {"Count": 1},
        "InputStartingPositionConfiguration": {"InputStartingPosition": "NOW"}
      }],
      "Outputs": [{
        "Name": "DESTINATION_SQL_STREAM",
        "KinesisStreamsOutput": {
          "ResourceARN": "<destination-stream-arn>",
          "RoleARN": "arn:aws:iam::<account-id>:role/<exec-role>"
        },
        "DestinationSchema": {"RecordFormatType": "JSON"}
      }]
    },
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "TextInput": "CREATE OR REPLACE PUMP \"SESSION_PUMP\" AS INSERT INTO DESTINATION_SQL_STREAM SELECT STREAM user_id, COUNT(*) AS event_count, SESSION_START() AS window_start, SESSION_END() AS window_end FROM SOURCE_SQL_STREAM_001 GROUP BY user_id, SESSION(event_time, INTERVAL '\''60'\'' SECONDS);"
      },
      "CodeContentType": "INLINE"
    }
  }' \
  --tags Environment=production,Application=<app-name>
```

## Step 5: CloudWatch log group

```bash
aws logs create-log-group --log-group-name <log-group>

aws logs put-retention-policy --log-group-name <log-group> --retention-in-days 30
```

## Step 6: Start the application

```bash
aws kinesisanalyticsv2 start-application \
  --application-name <app-name> \
  --run-configuration '{
    "FlinkRunConfiguration": {"AllowNonRestoredState": false},
    "ApplicationRestoreConfiguration": {
      "RestoreType": "RESTORE_FROM_LATEST_SNAPSHOT"
    }
  }'
```

Wait for `RUNNING`:

```bash
aws kinesisanalyticsv2 describe-application \
  --application-name <app-name> \
  --query 'ApplicationDetail.ApplicationStatus'
```

## Step 7: Application snapshots

```bash
# Create a snapshot before a code update
aws kinesisanalyticsv2 create-application-snapshot \
  --application-name <app-name> \
  --snapshot-name pre-update-$(date +%Y-%m-%d)

# List snapshots
aws kinesisanalyticsv2 list-application-snapshots \
  --application-name <app-name>
```

## Step 8: Update application code

```bash
aws kinesisanalyticsv2 update-application \
  --application-name <app-name> \
  --application-configuration-update '{
    "ApplicationCodeConfigurationUpdate": {
      "CodeContentUpdate": {
        "S3ContentLocationUpdate": {
          "FileKeyUpdate": "<new-code-key>"
        }
      }
    }
  }' \
  --current-application-version-id <version-id>
```

## Step 9: VPC access (private sources)

```bash
aws kinesisanalyticsv2 create-application \
  --application-name <app-name> \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::<account-id>:role/<exec-role> \
  --application-configuration '{
    "VpcConfiguration": {
      "SubnetIds": <vpc-subnet-ids>,
      "SecurityGroupIds": <security-group-ids>
    },
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::<code-bucket>",
          "FileKey": "<code-key>"
        }
      }
    }
  }'
```

## Step 10: Studio notebook (Zeppelin)

```bash
aws kinesisanalyticsv2 create-application \
  --application-name <notebook-name> \
  --runtime-environment ZEPPELIN-FLINK-1_0 \
  --service-execution-role arn:aws:iam::<account-id>:role/<exec-role> \
  --application-configuration '{
    "ZeppelinApplicationConfiguration": {
      "MonitoringConfiguration": {
        "LogLevel": "INFO"
      },
      "CatalogConfiguration": {
        "GlueDataCatalogConfiguration": {
          "DatabaseARN": "arn:aws:glue:<region>:<account-id>:database/default"
        }
      },
      "DeployAsApplicationConfiguration": {
        "CreateApplicationAsReadyForDeployment": true
      }
    }
  }' \
  --tags Environment=dev,Application=<notebook-name>
```

## Step 11: Verification

```bash
aws kinesisanalyticsv2 describe-application --application-name <app-name>
aws iam get-role --role-name <exec-role>
aws kinesis describe-stream --stream-name <source-stream-name>
aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/<app-name>
aws kinesisanalyticsv2 list-application-snapshots --application-name <app-name>
```

## Terraform equivalent

```hcl
resource "aws_kinesisanalyticsv2_application" "flink" {
  name                   = "fraud-detection-flink"
  runtime_environment    = "FLINK-1_19"
  service_execution_role = aws_iam_role.kda_exec.arn

  application_configuration {
    application_code_configuration {
      code_content {
        s3_content_location {
          bucket_arn = "arn:aws:s3:::kda-apps"
          file_key   = "fraud-detection-1.0.0.jar"
        }
      }
      code_content_type = "ZIPFILE"
    }

    flink_application_configuration {
      checkpoint_configuration {
        configuration_type            = "CUSTOM"
        checkpointing_enabled         = true
        checkpoint_interval           = 60000
        min_pause_between_checkpoints = 5000
      }

      parallelism_configuration {
        configuration_type  = "CUSTOM"
        parallelism         = 4
        parallelism_per_kpu = 1
      }

      monitoring_configuration {
        configuration_type = "CUSTOM"
        metrics_level      = "APPLICATION"
        log_level          = "INFO"
      }
    }

    environment_properties {
      property_group {
        property_group_id = "ConsumerConfig"
        property_map = {
          STREAM_NAME          = "transactions"
          AWS_REGION           = "us-east-1"
          SCAN_START_POSITION  = "LATEST"
        }
      }
    }
  }

  tags = {
    Environment  = "production"
    Application  = "fraud-detection"
  }
}
```

## CloudFormation equivalent

```yaml
Resources:
  KDAFlinkApplication:
    Type: AWS::KinesisAnalyticsV2::Application
    Properties:
      ApplicationName: fraud-detection-flink
      RuntimeEnvironment: FLINK-1_19
      ServiceExecutionRole: !GetAtt KDAExecutionRole.Arn
      ApplicationConfiguration:
        ApplicationCodeConfiguration:
          CodeContent:
            S3ContentLocation:
              BucketARN: !Sub "arn:aws:s3:::kda-apps"
              FileKey: "fraud-detection-1.0.0.jar"
          CodeContentType: ZIPFILE
        FlinkApplicationConfiguration:
          CheckpointConfiguration:
            ConfigurationType: CUSTOM
            CheckpointingEnabled: true
            CheckpointInterval: 60000
            MinPauseBetweenCheckpoints: 5000
          ParallelismConfiguration:
            ConfigurationType: CUSTOM
            Parallelism: 4
            ParallelismPerKPU: 1
          MonitoringConfiguration:
            ConfigurationType: CUSTOM
            MetricsLevel: APPLICATION
            LogLevel: INFO
        EnvironmentProperties:
          PropertyGroups:
            - PropertyGroupId: ConsumerConfig
              PropertyMap:
                STREAM_NAME: transactions
                AWS_REGION: !Ref AWS::Region
                SCAN_START_POSITION: LATEST
      Tags:
        - Key: Environment
          Value: production
        - Key: Application
          Value: fraud-detection
```
