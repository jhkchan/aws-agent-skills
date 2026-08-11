# CLI Commands and IaC — EMR Serverless Deployer

Full copy-pasteable CLI command sequence for all 11 deployment steps.
Variables to substitute: `<region>`, `<account-id>`, `<app-name>`,
`<release-label>`, `<type>`, `<exec-role>`, `<subnet-ids>`,
`<security-group-ids>`, `<log-bucket>`, `<log-prefix>`,
`<script-bucket>`, `<entry-point>`, `<initial-count>`, `<worker-cpu>`,
`<worker-memory>`, `<max-cpu>`, `<max-memory>`, `<image-uri>`.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

# Confirm execution role trust policy
aws iam get-role --role-name <exec-role> \
  --query 'Role.AssumeRolePolicyDocument'

# Confirm S3 log bucket exists
aws s3 ls s3://<log-bucket>/ 2>/dev/null || echo "Log bucket does not exist"

# Confirm entry-point script exists in S3
aws s3 ls s3://<script-bucket>/<entry-point> 2>/dev/null || echo "Script not found"

# Confirm VPC subnets exist (if VPC access needed)
aws ec2 describe-subnets --subnet-ids <subnet-ids> \
  --query 'Subnets[*].{ID:SubnetId,AZ:AvailabilityZone,Type:MapPublicIpOnLaunch}'

# Confirm security group outbound rules
aws ec2 describe-security-groups --group-ids <security-group-ids> \
  --query 'SecurityGroups[0].IpPermissionsEgress'

# Confirm latest stable release label
aws emr-serverless list-release-labels --query 'releaseLabels[-1]'

# Confirm service quota for capacity
aws service-quotas get-service-quota \
  --service-code emr-serverless \
  --quota-code L-XXXXXXXX \
  --query 'Quota.Value'

# Confirm Glue database exists (if catalog integration)
aws glue get-database --name <db-name> 2>/dev/null || echo "Glue database does not exist"
```

## Step 1: IAM execution role

```bash
aws iam create-role \
  --role-name <exec-role> \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "emr-serverless.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name <exec-role> \
  --policy-name emr-serverless-exec \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::etl-scripts",
          "arn:aws:s3:::etl-scripts/*",
          "arn:aws:s3:::raw-data",
          "arn:aws:s3:::raw-data/*"
        ]
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": [
          "arn:aws:s3:::curated/*",
          "arn:aws:s3:::<log-bucket>/*"
        ]
      },
      {
        "Effect": "Allow",
        "Action": ["glue:GetTable", "glue:GetDatabase", "glue:GetPartitions", "glue:CreateTable", "glue:UpdateTable"],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        "Resource": "arn:aws:logs:<region>:<account-id>:log-group:/aws/emr-serverless/*"
      },
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:<region>:<account-id>:secret:etl/*"
      }
    ]
  }'
```

## Step 2: S3 log bucket

```bash
aws s3api create-bucket \
  --bucket <log-bucket> \
  --region <region>

# Block public access
aws s3api put-public-access-block \
  --bucket <log-bucket> \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Lifecycle: transition to Glacier after 30 days, expire after 365 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket <log-bucket> \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "log-archive",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "Transitions": [{"Days": 30, "StorageClass": "GLACIER"}],
      "Expiration": {"Days": 365}
    }]
  }'
```

## Step 3: Create the application

```bash
APP_ID=$(aws emr-serverless create-application \
  --name <app-name> \
  --release-label <release-label> \
  --type <type> \
  --initial-capacity '[{
    "workerType": {
      "cpu": "<worker-cpu>",
      "memory": "<worker-memory>",
      "disk": "20 GB"
    },
    "initialCount": <initial-count>
  }]' \
  --maximum-capacity '{
    "cpu": "<max-cpu>",
    "memory": "<max-memory>",
    "disk": "4000 GB"
  }' \
  --network-configuration '{
    "subnetIds": ["<subnet-1>", "<subnet-2>"],
    "securityGroupIds": ["<sg-1>"]
  }' \
  --auto-start-configuration '{"enabled": true}' \
  --auto-stop-configuration '{"enabled": true, "idleTimeoutMinutes": 15}' \
  --tags Environment=production,Application=<app-name> \
  --query 'applicationId' --output text)

echo "Application ID: $APP_ID"
```

## Step 4: Start the application

```bash
aws emr-serverless start-application --application-id "$APP_ID"

# Wait for STARTED state
while [ "$(aws emr-serverless get-application --application-id "$APP_ID" --query 'application.state' --output text)" != "STARTED" ]; do
  echo "Waiting for application to start..."
  sleep 10
done
echo "Application is STARTED"
```

## Step 5: Configure pre-initialized capacity (warm workers)

```bash
aws emr-serverless update-application \
  --application-id "$APP_ID" \
  --initial-capacity '[{
    "workerType": {
      "cpu": "<worker-cpu>",
      "memory": "<worker-memory>",
      "disk": "20 GB"
    },
    "initialCount": <initial-count>
  }]'
```

## Step 6: Job submission (Spark)

```bash
JOB_RUN_ID=$(aws emr-serverless start-job-run \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::<account-id>:role/<exec-role> \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://<script-bucket>/<entry-point>",
      "entryPointArguments": [
        "--source", "s3://raw-data/events/",
        "--target", "s3://curated/events/"
      ],
      "sparkSubmitParameters": "--conf spark.sql.shuffle.partitions=200 --conf spark.sql.adaptive.enabled=true --conf spark.executor.memoryOverhead=2g"
    }
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://<log-bucket>/<log-prefix>/"},
      "managedPersistentAppUI": "ENABLED",
      "cloudWatchLoggingConfiguration": {
        "enabled": true,
        "logGroupName": "/aws/emr-serverless/<app-name>",
        "logStreamNamePrefix": "job"
      }
    },
    "applicationConfiguration": [
      {
        "classification": "spark-defaults",
        "properties": {
          "spark.sql.shuffle.partitions": "200",
          "spark.sql.adaptive.enabled": "true",
          "spark.sql.adaptive.coalescePartitions.enabled": "true",
          "spark.executor.memoryOverhead": "2g",
          "spark.serializer": "org.apache.spark.serializer.KryoSerializer"
        }
      }
    ]
  }' \
  --name "<job-name>" \
  --tags Environment=production,Pipeline=daily-transform \
  --query 'jobRunId' --output text)

echo "Job Run ID: $JOB_RUN_ID"
```

## Step 7: Job submission (Hive)

```bash
JOB_RUN_ID=$(aws emr-serverless start-job-run \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::<account-id>:role/<exec-role> \
  --job-driver '{
    "hive": {
      "query": "SELECT COUNT(*) FROM sales WHERE dt = '\''2026-08-11'\''",
      "initScriptFileS3Path": "s3://<script-bucket>/hive-init.sql",
      "parameters": "--hiveconf hive.execution.engine=tez"
    }
  }' \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://<log-bucket>/hive/"},
      "cloudWatchLoggingConfiguration": {"enabled": true}
    }
  }' \
  --name "<hive-job-name>" \
  --query 'jobRunId' --output text)
```

## Step 8: Configuration overrides (Spark tuning)

Configuration overrides are applied at the application level and can
be overridden per-job via `sparkSubmitParameters`.

```bash
aws emr-serverless update-application \
  --application-id "$APP_ID" \
  --configuration-overrides '{
    "applicationConfiguration": [
      {
        "classification": "spark-defaults",
        "properties": {
          "spark.sql.shuffle.partitions": "200",
          "spark.sql.adaptive.enabled": "true",
          "spark.sql.adaptive.coalescePartitions.enabled": "true",
          "spark.sql.adaptive.skewJoin.enabled": "true",
          "spark.executor.memoryOverhead": "2g",
          "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
          "spark.sql.parquet.compression.codec": "snappy"
        }
      },
      {
        "classification": "yarn-site",
        "properties": {
          "yarn.nodemanager.vmem-check-enabled": "false",
          "yarn.nodemanager.pmem-check-enabled": "false"
        }
      }
    ]
  }'
```

## Step 9: VPC access (private resources)

```bash
aws emr-serverless update-application \
  --application-id "$APP_ID" \
  --network-configuration '{
    "subnetIds": ["subnet-aaa", "subnet-bbb", "subnet-ccc"],
    "securityGroupIds": ["sg-emr-prod"]
  }'
```

## Step 10: Interactive endpoint (Spark Connect)

```bash
aws emr-serverless create-interactive-endpoint \
  --application-id "$APP_ID" \
  --execution-role-arn arn:aws:iam::<account-id>:role/<exec-role> \
  --release-label <release-label> \
  --configuration-overrides '{
    "monitoringConfiguration": {
      "s3MonitoringConfiguration": {"logUri": "s3://<log-bucket>/interactive/"},
      "cloudWatchLoggingConfiguration": {"enabled": true, "logGroupName": "/aws/emr-serverless/<app-name>-interactive"}
    }
  }'

# Connect from a Spark Connect client
# spark-shell --remote sc://<endpoint-host>:443
# or in PySpark:
# from pyspark.sql.connect import SparkSession
# spark = SparkSession.builder.remote("sc://<endpoint-host>:443").getOrCreate()
```

## Step 11: Post-deployment verification

```bash
aws emr-serverless get-application --application-id "$APP_ID"
aws emr-serverless list-job-runs --application-id "$APP_ID"
aws emr-serverless get-job-run --application-id "$APP_ID" --job-run-id "$JOB_RUN_ID"
aws iam get-role --role-name <exec-role>
aws s3 ls s3://<log-bucket>/<log-prefix>/
aws logs describe-log-groups --log-group-name-prefix /aws/emr-serverless/<app-name>
aws emr-serverless list-tags-for-resource --resource-arn arn:aws:emr-serverless:<region>:<account-id>:application/<app-id>
```

## Terraform equivalents

### Application

```hcl
resource "aws_emrserverless_application" "etl_spark" {
  name          = "etl-spark-prod"
  release_label = "emr-7.2.0"
  type          = "SPARK"

  initial_capacity {
    initial_count = 50

    worker_configuration {
      cpu    = "4 vCPU"
      memory = "16 GB"
      disk   = "20 GB"
    }
  }

  maximum_capacity {
    cpu    = "800 vCPU"
    memory = "3200 GB"
    disk   = "4000 GB"
  }

  network_configuration {
    subnet_ids         = [aws_subnet.a.id, aws_subnet.b.id]
    security_group_ids = [aws_security_group.emr.id]
  }

  auto_start_configuration {
    enabled = true
  }

  auto_stop_configuration {
    enabled              = true
    idle_timeout_minutes = 15
  }

  configuration_overrides = jsonencode({
    monitoringConfiguration = {
      s3MonitoringConfiguration = {
        logUri = "s3://${aws_s3_bucket.emr_logs.bucket}/etl-spark-prod/"
      }
      cloudWatchLoggingConfiguration = {
        enabled         = true
        logGroupName    = "/aws/emr-serverless/etl-spark-prod"
        logStreamNamePrefix = "job"
      }
    }
    applicationConfiguration = [
      {
        classification = "spark-defaults"
        properties = {
          "spark.sql.adaptive.enabled"      = "true"
          "spark.sql.shuffle.partitions"    = "200"
          "spark.executor.memoryOverhead"   = "2g"
        }
      }
    ]
  })

  tags = {
    Environment = "production"
    Application = "etl-spark"
  }
}
```

### Job run

```hcl
resource "aws_emrserverless_job_run" "daily_transform" {
  application_id      = aws_emrserverless_application.etl_spark.id
  execution_role_arn  = aws_iam_role.emr_exec.arn
  name                = "daily-transform-2026-08-11"
  release_label       = "emr-7.2.0"

  job_driver {
    spark_submit {
      entry_point = "s3://${aws_s3_bucket.scripts.bucket}/daily_transform.py"
      entry_point_arguments = [
        "--source", "s3://raw-data/events/",
        "--target", "s3://curated/events/"
      ]
      spark_submit_parameters = "--conf spark.sql.shuffle.partitions=200 --conf spark.sql.adaptive.enabled=true"
    }
  }

  configuration_overrides = jsonencode({
    monitoringConfiguration = {
      s3MonitoringConfiguration = {
        logUri = "s3://${aws_s3_bucket.emr_logs.bucket}/etl-spark-prod/"
      }
    }
  })
}
```

## CloudFormation equivalents

### Application

```yaml
Type: AWS::EMRServerless::Application
Properties:
  Name: etl-spark-prod
  ReleaseLabel: emr-7.2.0
  Type: SPARK
  InitialCapacity:
    - WorkerType:
        Cpu: 4 vCPU
        Memory: 16 GB
        Disk: 20 GB
      InitialCount: 50
  MaximumCapacity:
    Cpu: 800 vCPU
    Memory: 3200 GB
    Disk: 4000 GB
  NetworkConfiguration:
    SubnetIds:
      - !Ref SubnetA
      - !Ref SubnetB
    SecurityGroupIds:
      - !Ref EMRSecurityGroup
  AutoStartConfiguration:
    Enabled: true
  AutoStopConfiguration:
    Enabled: true
    IdleTimeoutMinutes: 15
  Tags:
    - Key: Environment
      Value: production
    - Key: Application
      Value: etl-spark
```
