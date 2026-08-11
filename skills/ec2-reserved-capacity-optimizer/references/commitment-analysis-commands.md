# Commitment Analysis Commands — Reference

Supplementary reference for the EC2 Reserved Capacity Optimizer skill.
The canonical command script per commitment optimization dimension.

## Universal first commands (run for any RI/SP review)

```bash
# 1. List active Reserved Instances:
aws ec2 describe-reserved-instances \
  --filters Name=state,Values=active \
  --query 'ReservedInstances[*].{id:ReservedInstancesId,type:InstanceType,offeringClass:OfferingClass,offeringType:OfferingType,duration:Duration,start:Start,az:AvailabilityZone,count:InstanceCount,tenancy:InstanceTenancy,state:State}'

# 2. List active Savings Plans:
aws savingsplans describe-savings-plans \
  --states ACTIVE \
  --query 'savingsPlans[*].{id:savingsPlanId,type:savingsPlanType,commitment:commitment,term:termInYears/12,payment:paymentOption,state:state,start:startTime,end:endTime}'

# 3. Pull RI utilization (last 30 days):
aws ce get-reservation-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Compute Cloud - Compute"]}}'

# 4. Pull RI coverage (last 30 days):
aws ce get-reservation-coverage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Compute Cloud - Compute"]}}'

# 5. Pull SP utilization (last 30 days):
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY

# 6. Pull SP coverage (last 30 days):
aws ce get-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY
```

## Dimension A: Coverage gap — purchase recommendation

```bash
# Get Cost Explorer RI purchase recommendation (Standard, 1yr):
aws ce get-reservation-purchase-recommendation \
  --service "Amazon Elastic Compute Cloud - Compute" \
  --term-in-years 1 \
  --payment-option NO_UPFRONT \
  --lookback-period 60 \
  --service-specification '{"EC2Specification":{"OfferingClass":"STANDARD"}}'

# Get Savings Plans purchase recommendation:
aws ce get-savings-plans-purchase-recommendation \
  --lookback-period 60 \
  --term-in-years 1 \
  --payment-option NO_UPFRONT

# Get EC2 fleet instance-type distribution:
aws ec2 describe-instances \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[*].Instances[*].InstanceType' \
  --output text | tr '\t' '\n' | sort | uniq -c | sort -rn
```

## Dimension B: Utilization gap — RI detail by instance type

```bash
# RI utilization by instance type (monthly):
aws ce get-reservation-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Compute Cloud - Compute"]}}'

# SP utilization detail by instance family:
aws ce get-savings-plans-utilization-detail \
  --time-period Start=2026-07-01,End=2026-08-01
```

## Dimension C: Convertible RI exchange

```bash
# Get exchange quote for Convertible RI:
aws ec2 get-reserved-instances-exchange-quote \
  --reserved-instance-ids <ri-id> \
  --target-configurations '[{"InstanceType":"m5.xlarge","Scope":"AvailabilityZone","AvailabilityZone":"us-east-1a","InstanceCount":1,"OfferingClass":"convertible","InstanceTenancy":"default","ProductDescription":"Linux/UNIX"}]'

# Perform the exchange:
aws ec2 accept-reserved-instances-exchange-quote \
  --reserved-instance-ids <ri-id> \
  --target-configurations '[{"InstanceType":"m5.xlarge","Scope":"AvailabilityZone","AvailabilityZone":"us-east-1a","InstanceCount":1,"OfferingClass":"convertible","InstanceTenancy":"default","ProductDescription":"Linux/UNIX"}]'
```

## Dimension D: RI Marketplace — sell Standard RIs

```bash
# List a Standard RI for sale on the Marketplace:
aws ec2 create-reserved-instances-listing \
  --client-token <unique-token> \
  --instance-count 1 \
  --price-schedules '[{"Price":<price>,"Term":<remaining-months>,"CurrencyCode":"USD"}]' \
  --reserved-instances-id <ri-id>

# Check existing Marketplace listings:
aws ec2 describe-reserved-instances-listings

# Cancel a listing:
aws ec2 cancel-reserved-instances-listing \
  --reserved-instances-listing-id <listing-id>
```

## Dimension E: CloudWatch / Budgets utilization alerts

```bash
# Create CloudWatch alarm for RI utilization below 80%:
aws cloudwatch put-metric-alarm \
  --alarm-name "RI-Utilization-Below-80" \
  --namespace AWS/Billing \
  --metric-name "TotalRIUtilization" \
  --threshold 80 \
  --comparison-operator LessThanThreshold \
  --period 86400 \
  --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>

# Create a Cost and Usage Budget for EC2 on-demand spend:
aws budgets create-budget \
  --account-id <account-id> \
  --budget file://ec2-ondemand-budget.json \
  --notifications-with-subscribers file://ec2-ondemand-notifications.json
```

## Verification commands (post-optimization)

```bash
# Verify RI utilization after purchase (14-day check):
aws ce get-reservation-utilization \
  --time-period Start=2026-07-15,End=2026-07-29 \
  --granularity DAILY \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE

# Verify SP coverage after purchase:
aws ce get-savings-plans-coverage \
  --time-period Start=2026-07-15,End=2026-07-29 \
  --granularity DAILY

# Check on-demand spend ratio (should decrease after commitment):
aws ce get-cost-and-usage \
  --time-period Start=2026-07-15,End=2026-07-29 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"PurchaseType","Values":["On-Demand Instances"]}}' \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE
```
