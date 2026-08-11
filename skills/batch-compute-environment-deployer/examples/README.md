# Example: Deploy AWS Batch Compute Environment

## Scenario
Deploy an EC2 compute environment with BEST_FIT_PROGRESSIVE, a Fargate fallback, and a production job queue.

## Steps

### 1. Create EC2 Spot Compute Environment (Primary)
```bash
aws batch create-compute-environment \
  --compute-environment-name batch-spot-prod \
  --type MANAGED \
  --state ENABLED \
  --compute-resources type=EC2,minvCpus=0,maxvCpus=1000,desiredvCpus=0,\
instanceTypes=m5.large,m5.xlarge,c5.large,c5.xlarge,\
allocationStrategy=SPOT_CAPACITY_OPTIMIZED,\
subnets=subnet-aaa11122,subnet-bbb22233,\
securityGroupIds=sg-batch111,\
instanceRole=arn:aws:iam::123456789012:instance-profile/batch-instance-profile,\
spotIamFleetRole=arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet
```

### 2. Create On-Demand Fallback Compute Environment
```bash
aws batch create-compute-environment \
  --compute-environment-name batch-ondemand-fallback \
  --type MANAGED \
  --state ENABLED \
  --compute-resources type=EC2,minvCpus=0,maxvCpus=200,desiredvCpus=0,\
instanceTypes=m5.large,m5.xlarge,\
allocationStrategy=BEST_FIT_PROGRESSIVE,\
subnets=subnet-aaa11122,subnet-bbb22233,\
securityGroupIds=sg-batch111,\
instanceRole=arn:aws:iam::123456789012:instance-profile/batch-instance-profile
```

### 3. Create Job Queue (Spot primary, On-Demand fallback)
```bash
aws batch create-job-queue \
  --job-queue-name production-queue \
  --priority 500 \
  --compute-environment-order \
    order=1,computeEnvironment=batch-spot-prod \
    order=2,computeEnvironment=batch-ondemand-fallback
```

### 4. Register Job Definition
```bash
aws batch register-job-definition \
  --job-definition-name data-etl-v1 \
  --type container \
  --container-properties image=123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest,vcpus=2,memory=4096
```

## Key Decisions
- Spot primary saves 60-70% on compute costs
- BEST_FIT_PROGRESSIVE for fallback ensures instance availability
- Queue order ensures spot is always tried first
- Array jobs (size=100) for parallel ETL processing
