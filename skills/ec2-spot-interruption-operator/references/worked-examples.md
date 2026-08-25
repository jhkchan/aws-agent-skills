# EC2 Spot Interruption - Worked Examples

Additional worked examples (the primary handle-interruption example stays
in SKILL.md). Same output contract.

### Worked example — tune-replacement-strategy (REVIEW_REQUIRED)

```text
OPERATION: tune-replacement-strategy
VERDICT: REVIEW_REQUIRED
TARGET: prod-batch-fleet (Spot Fleet: sfr-batch-prod, current strategy: lowestPrice, target: capacity-optimized)
PRE_CHECKS:
  - [PASS] Spot Fleet sfr-batch-prod State: active
  - [PASS] TargetCapacity: 50, FulfilledCapacity: 47 (3 instances
    recently interrupted)
  - [REVIEW] Current AllocationStrategy: lowestPrice with
    InstancePoolsToUseCount: 1 (single pool — highest interruption
    risk). Proposed: capacity-optimized with the existing 5-instance-
    type diversification. This changes the pool selection logic —
    new launches will prefer lower-interruption pools over cheaper
    ones. Estimated cost impact: +5-8% on Spot spend. Confirm the
    cost increase is acceptable for the availability improvement.
  - [REVIEW] Current diversification: 2 instance families (c5, m5)
    across 2 AZs (us-east-1a, us-east-1b). Below the 3x3 minimum
    for 99.9% availability. Proposed: add c6g (Graviton) and
    us-east-1c. Confirm the batch workload supports arm64.
STEPS:
  1. CONFIRM: About to modify Spot Fleet sfr-batch-prod: change
     AllocationStrategy from lowestPrice to capacity-optimized, add
     c6g.large and c6g.xlarge to the LaunchTemplate Overrides, add
     us-east-1c to the AZ list. This takes effect immediately for
     new launches. Existing instances are not restarted. Proceed?
     (yes/no)
  2. aws ec2 modify-spot-fleet-request \
       --spot-fleet-request-id sfr-batch-prod \
       --target-capacity 50 \
       --excess-capacity-termination-policy true \
       --launch-template-configs '[{
         "LaunchTemplateSpecification": {
           "LaunchTemplateId": "lt-batch-prod",
           "Version": "2"
         },
         "Overrides": [
           {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1a"},
           {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1b"},
           {"InstanceType": "c5.large", "AvailabilityZone": "us-east-1c"},
           {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1a"},
           {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1b"},
           {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1c"},
           {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1a"},
           {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1b"},
           {"InstanceType": "c6g.large", "AvailabilityZone": "us-east-1c"}
         ]
       }]'
  3. Monitor interruption rate over 24-48 hours:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/Usage \
       --metric-name CallCount \
       --dimensions Name=Service,Value=EC2 Name=Resource,Value=Spot \
       --start-time $(date -u -v-2d +%Y-%m-%dT%H:%M:%SZ) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
       --period 3600 --statistics Sum
POST_VERIFY:
  - (pending execution)
  - [PASS] AllocationStrategy: capacity-optimized (confirmed via
    describe-spot-fleet-requests)
  - [PASS] Diversification: 3 families (c5, m5, c6g) x 3 AZs (1a, 1b, 1c)
  - [PASS] Spot Fleet FulfilledCapacity: 50 (full capacity within 10 min)
  - [PASS] 48-hour interruption count: 2 (down from 12 in the prior
    48-hour window with lowestPrice + single pool)
NOTES:
  - The switch from lowestPrice to capacity-optimized typically reduces
    interruption frequency by 5-10x. The cost increase is 5-8% because
    capacity-optimized does not always select the cheapest pool.
  - Graviton (c6g) instances often have lower interruption rates than
    x86 (c5/m5) due to newer capacity. Confirm the batch application
    runs on arm64 (recompile or use multi-arch container images).
  - The 3x3 diversification (9 pools) provides a 99.9% Spot availability
    profile — the probability of all 9 pools being interrupted
    simultaneously is negligible.
```

### Worked example — configure-pipeline (condensed)

```text
OPERATION: configure-pipeline
VERDICT: REVIEW_REQUIRED
TARGET: prod-api-asg (graceful-shutdown pipeline: EventBridge + SQS + Lambda)
PRE_CHECKS:
  - [PASS] ASG exists, uses Spot via MixedInstancesPolicy
  - [PASS] ALB target group exists (deregistration_delay: 300 — needs
    change to 45 for Spot)
  - [REVIEW] Pipeline: EventBridge -> SQS (with DLQ) -> Lambda
    (timeout 90, reserved concurrency 10). Lambda deregisters from ELB,
    sends SIGTERM via SSM, writes checkpoint to S3. Confirm bucket +
    Lambda role permissions.
  - [REVIEW] ALB deregistration_delay change 300 -> 45: affects ALL
    Spot targets. Confirm app drains in-flight requests within 45s.
STEPS:
  1. CONFIRM: configure Spot interruption pipeline for prod-api-asg
     (EventBridge rule, SQS+DLQ, Lambda, modify ELB delay to 45s).
     Proceed? (yes/no)
  2. aws sqs create-queue --queue-name spot-interruption-queue
  3. aws sqs set-queue-attributes --queue-url <url> \
       --attributes RedrivePolicy='{"deadLetterTargetArn":"...:dlq","maxReceiveCount":"3"}'
  4. aws events put-rule --name spot-interruption-warning \
       --event-pattern '{"detail-type":["EC2 Spot Instance Interruption Warning"],"source":["aws.ec2"]}'
  5. aws events put-targets --rule spot-interruption-warning \
       --targets '[{"Id":"1","Arn":"arn:aws:sqs:us-east-1:...:spot-interruption-queue"}]'
  6. aws lambda create-function --function-name prod-spot-graceful-shutdown \
       --runtime python3.12 --handler index.lambda_handler \
       --role arn:aws:iam::...:role/spot-shutdown-role \
       --timeout 90 --code S3Bucket=prod-lambda-artifacts,S3Key=spot-shutdown/latest.zip
  7. aws lambda put-function-concurrency --function-name prod-spot-graceful-shutdown \
       --reserved-concurrent-executions 10
  8. aws elbv2 modify-target-group-attributes --target-group-arn <arn> \
       --attributes Key=deregistration_delay.timeout_seconds,Value=45
  9. aws autoscaling put-lifecycle-hook --auto-scaling-group-name prod-api-asg \
       --lifecycle-hook-name spot-termination-hook \
       --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
       --heartbeat-timeout 120 --default-result CONTINUE
POST_VERIFY: (pending) — rule ENABLED, SQS DLQ configured, Lambda Active,
  ELB delay 45, lifecycle hook 120s. Synthetic test passes.
NOTES: Test with synthetic event BEFORE relying on it. 45s delay leaves
  75s for checkpointing. Monitor SQS depth — stale messages mean Lambda
  is lagging.
```

