# Auto-Scaling and Health — Elastic Beanstalk Environment Optimizer

Deep reference on auto-scaling policy tuning (right-sizing min/max/
desired, threshold tuning, scaling trigger selection), health check
configuration (health check URL, timeout, threshold tuning to reduce
false alarms), .ebextensions optimization (auditing, removing unused
resources, cleanup), and environment tier (web server vs worker).
Loaded on demand by the skill — kept out of the main SKILL.md body so
the optimization procedure stays scannable.

## Auto-scaling policy tuning

### Right-sizing capacity

Auto-scaling capacity (min/max/desired) should match the workload
pattern. Over-provisioning wastes money; under-provisioning causes
performance degradation.

**Capacity guidelines by environment purpose:**

| Environment | Min | Max | Desired | Rationale |
|---|---|---|---|---|
| Dev | 1 | 1 | 1 | No scaling, cheapest |
| Staging | 1 | 2 | 1 | Limited scaling for testing |
| Production (low traffic) | 2 | 4 | 2 | Multi-AZ HA, modest scaling |
| Production (high traffic) | 3+ | N | 3+ | Based on peak traffic analysis |
| Worker tier | 1 | N | 1 | Scales with queue depth |

**Analyze traffic patterns for capacity tuning:**

```bash
# Get average CPU utilization by hour over 7 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/AutoScaling \
  --metric-name GroupDesiredCapacity \
  --dimensions Name=AutoScalingGroupName,Values=awseb-e-xxx-stack-AutoScalingGroup-xxx \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average Maximum \
  --output table --region us-east-1

# Get EC2 CPU utilization pattern
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Values=i-xxx \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average Maximum \
  --output table --region us-east-1
```

### Scaling trigger tuning

The scaling trigger determines when Elastic Beanstalk adds or removes
instances. The default trigger is CPU utilization.

**Default trigger settings:**

| Setting | Default | Recommendation |
|---|---|---|
| MeasureName | CPUUtilization | Keep for CPU-bound apps |
| Statistic | Average | Keep |
| Unit | Percent | Keep |
| LowerThreshold | 20 | Tune based on app |
| UpperThreshold | 80 | Tune based on app |
| BreachDuration | 300 (5 min) | Increase to reduce flapping |
| LowerBreachScaleIncrement | -1 | Keep |
| UpperBreachScaleIncrement | 1 | Increase to 2 for faster scale-out |

**Common trigger issues:**

```text
Issue 1: Scaling too aggressively (flapping)
  Symptom: instances constantly being added/removed
  Fix: increase BreachDuration from 300 to 600 seconds
  Fix: widen thresholds (LowerThreshold=15, UpperThreshold=85)

Issue 2: Scaling too slowly
  Symptom: slow response to traffic spikes
  Fix: decrease BreachDuration from 300 to 120 seconds
  Fix: increase UpperBreachScaleIncrement from 1 to 2

Issue 3: Scaling on wrong metric
  Symptom: CPU-based trigger but app is memory-bound
  Fix: switch MeasureName to memory utilization (requires custom metric)
  Alternative: use ALB RequestCountPerTarget for request-driven scaling
```

### Update auto-scaling configuration

```bash
# Update capacity
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=6 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=3 \
  --region us-east-1

# Update trigger thresholds
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:autoscaling:trigger,OptionName=MeasureName,Value=CPUUtilization \
    Namespace=aws:autoscaling:trigger,OptionName=Statistic,Value=Average \
    Namespace=aws:autoscaling:trigger,OptionName=Unit,Value=Percent \
    Namespace=aws:autoscaling:trigger,OptionName=LowerThreshold,Value=20 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperThreshold,Value=70 \
    Namespace=aws:autoscaling:trigger,OptionName=BreachDuration,Value=300 \
    Namespace=aws:autoscaling:trigger,OptionName=LowerBreachScaleIncrement,Value=-1 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperBreachScaleIncrement,Value=1 \
  --region us-east-1
```

## Health check tuning

### Health check URL

The health check URL determines what path Elastic Beanstalk polls to
determine if the application is healthy. A wrong path causes false
unhealthy status.

**Configure health check URL:**

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:elasticbeanstalk:application,OptionName=Application Healthcheck URL,Value=/health \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced \
  --region us-east-1
```

**Best practices for health check endpoint:**
- Implement a dedicated `/health` endpoint that returns HTTP 200
- The endpoint should check critical dependencies (database, cache)
- Keep the response fast (under 1 second) to avoid timeout
- Do NOT include heavy logic or auth in the health check

### Health check common issues

```text
Issue 1: Health check URL returns 404
  Symptom: all instances marked unhealthy
  Cause: health check URL path does not exist in the app
  Fix: add a /health endpoint or change the URL to an existing path

Issue 2: Health check timeout during startup
  Symptom: instances marked unhealthy during deployment
  Cause: application takes longer than the health check grace period to start
  Fix: increase the health check grace period

Issue 3: Health check too sensitive
  Symptom: instances marked unhealthy on brief CPU spikes
  Cause: health check interval or threshold too aggressive
  Fix: increase the interval and failure threshold

Issue 4: ELB health check vs EC2 health check mismatch
  Symptom: ELB says healthy but EC2 says degraded
  Cause: different health check criteria at each layer
  Fix: align the health check configuration across ELB and EC2
```

### ELB health check tuning

```bash
# Tune ELB health check settings
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:elasticbeanstalk:environment:process:default,OptionName=HealthCheckPath,Value=/health \
    Namespace=aws:elasticbeanstalk:environment:process:default,OptionName=HealthCheckInterval,Value=15 \
    Namespace=aws:elasticbeanstalk:environment:process:default,OptionName=HealthCheckTimeout,Value=5 \
    Namespace=aws:elasticbeanstalk:environment:process:default,OptionName=HealthyThresholdCount,Value=3 \
    Namespace=aws:elasticbeanstalk:environment:process:default,OptionName=UnhealthyThresholdCount,Value=5 \
  --region us-east-1
```

| Setting | Default | Recommendation |
|---|---|---|
| HealthCheckPath | / | /health (dedicated endpoint) |
| HealthCheckInterval | 10 sec | 15 sec (reduce noise) |
| HealthCheckTimeout | 5 sec | 5 sec (keep) |
| HealthyThresholdCount | 3 | 3 (keep) |
| UnhealthyThresholdCount | 3 | 5 (more tolerant of brief issues) |

## .ebextensions optimization

### What .ebextensions does

`.ebextensions/*.config` files contain YAML configuration that Elastic
Beanstalk applies during environment creation and deployment. They can
create AWS resources, install packages, write files, and run commands.

### Audit .ebextensions

```bash
# List all .ebextensions files
ls -la .ebextensions/

# Show the content of each config file
for f in .ebextensions/*.config; do
  echo "=== $f ==="
  cat "$f"
  echo
done

# Search for resource creation (potential unused resources)
grep -rn "Resources:" .ebextensions/
grep -rn "Type: AWS::" .ebextensions/

# Search for commands (potential one-time setup left in)
grep -rn "commands:" .ebextensions/
grep -rn "leader_only:" .ebextensions/
```

### Common .ebextensions issues

```text
Issue 1: Unused resources
  Resources created for testing but never removed
  Example: an S3 bucket or SQS queue created in .ebextensions
  Cost impact: ongoing charges for unused resources
  Fix: remove the Resources block

Issue 2: Duplicate entries across files
  Same package installed in multiple config files
  Impact: slower deployments (redundant installs)
  Fix: consolidate into a single config file

Issue 3: One-time commands left in
  Commands that set up initial state (create database schema)
  Impact: runs on every deployment, slowing it down
  Fix: wrap in a leader_only check or move to CI/CD pipeline

Issue 4: Hardcoded values
  AMI IDs, instance types, or region names hardcoded in config
  Impact: breaks when deploying to different regions
  Fix: use Elastic Beanstalk environment properties or CloudFormation refs
```

### .ebextensions cleanup example

```yaml
# BEFORE: .ebextensions/old-setup.config (unused resources)
Resources:
  TestBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-test-bucket-old-xxx

files:
  "/opt/elasticbeanstalk/hooks/appdeploy/post/01_test.sh":
    mode: "000755"
    content: |
      #!/bin/bash
      echo "This was a test script, no longer needed"

commands:
  01_create_table:
    command: "psql -c 'CREATE TABLE IF NOT EXISTS test_data...'"
    leader_only: true

# AFTER: Remove the entire file (all resources are unused)
# Or keep only what is actively needed:
# (delete TestBucket resource, delete test script, move schema creation to CI/CD)
```

## Environment tier: web server vs worker

### Web server tier

The web server tier serves HTTP/HTTPS requests behind a load balancer.
Each instance runs an application that handles incoming requests.

```text
Web server tier architecture:
  Internet → Route 53 → ALB → EC2 instances (app)

  Cost components:
    - EC2 instances
    - Application Load Balancer (if load-balanced)
    - NAT Gateway (if private subnet)
```

### Worker tier

The worker tier processes background jobs from an SQS queue. No load
balancer is needed (SQS is the entry point).

```text
Worker tier architecture:
  App → SQS queue → EC2 instances (worker daemon)

  Cost components:
    - EC2 instances
    - SQS (very cheap, ~$0.40 per million requests)
    - NO Application Load Balancer
    - NO NAT Gateway (if instances are in private subnet with VPC endpoints)

  Worker tier eliminates:
    - ALB cost (~$18/mo)
    - Reduces data transfer (SQS vs HTTP)
```

### Switch from web server to worker tier

```bash
# Create a new worker environment
aws elasticbeanstalk create-environment \
  --application-name my-app \
  --environment-name my-worker-env \
  --solution-stack-name "64bit Amazon Linux 2023 v6.0.0 running Node.js 20" \
  --tier Name=Worker,Type=SQS,Version=1.0 \
  --option-settings \
    Namespace=aws:elasticbeanstalk:sqsd,OptionName=WorkerQueueURL,Value=https://sqs.us-east-1.amazonaws.com/123456789012/my-queue \
    Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small \
  --region us-east-1
```

**Key optimization:** worker environments do not need an ALB. For
background processing workloads, using a worker tier saves ~$18/month
(ALB) and is more resilient (SQS retries failed messages).

## Cost-optimized auto-scaling example

```bash
# Dev: no scaling (min=max=desired=1)
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=1 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=1 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=1 \
  --region us-east-1

# Production: right-sized scaling with tuned triggers
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=6 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=3 \
    Namespace=aws:autoscaling:trigger,OptionName=MeasureName,Value=CPUUtilization \
    Namespace=aws:autoscaling:trigger,OptionName=LowerThreshold,Value=20 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperThreshold,Value=70 \
    Namespace=aws:autoscaling:trigger,OptionName=BreachDuration,Value=300 \
  --region us-east-1
```

## Opt 7 — right-size capacity command (from SKILL.md)

```bash
# Set min/max/desired capacity based on traffic analysis
# For dev: min=1, max=1, desired=1 (no scaling)
# For staging: min=1, max=2, desired=1 (limited scaling)
# For prod: min=2, max=N (based on peak traffic)
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=6 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=2 \
  --region us-east-1
```

## Opt 7 — tune scaling triggers command (from SKILL.md)

```bash
# Use CPU utilization as the scaling trigger (default)
# Adjust thresholds based on steady-state CPU patterns
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:autoscaling:trigger,OptionName=MeasureName,Value=CPUUtilization \
    Namespace=aws:autoscaling:trigger,OptionName=Statistic,Value=Average \
    Namespace=aws:autoscaling:trigger,OptionName=Unit,Value=Percent \
    Namespace=aws:autoscaling:trigger,OptionName=LowerThreshold,Value=20 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperThreshold,Value=70 \
    Namespace=aws:autoscaling:trigger,OptionName=LowerBreachScaleIncrement,Value=-1 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperBreachScaleIncrement,Value=1 \
    Namespace=aws:autoscaling:trigger,OptionName=BreachDuration,Value=300 \
  --region us-east-1
```

## Opt 10 — common health check issues (from SKILL.md)

- Health check URL path is wrong (returns 404, marked unhealthy).
- Health check timeout is too short (marks instances unhealthy before
  the application starts up).
- Threshold too sensitive (marks instances unhealthy on brief CPU spike).

## Opt 10 — tune health check command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:application,OptionName=Application Healthcheck URL,Value=/health \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced \
  --region us-east-1
```

## Opt 11 — disable termination protection command (from SKILL.md)

```bash
# Only for dev/staging environments that should be torn down
aws elasticbeanstalk update-environment \
  --environment-name my-dev-env \
  --no-terminate-on-failure \
  --region us-east-1
```
