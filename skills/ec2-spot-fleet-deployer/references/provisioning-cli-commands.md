# Provisioning CLI Commands — EC2 Spot Fleet Deployer

Full copy-pasteable CLI command sequence for provisioning EC2 Spot
Fleets with launch templates, allocation strategies, capacity
rebalance, Spot placement score, and capacity reservations.
Variables to substitute: `<region>`, `<account-id>`, `<ami-id>`,
`<lt-id>`, `<fleet-id>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm Spot Fleet service-linked role exists
aws iam get-role --role-name AWSServiceRoleForEC2SpotFleet \
  --query 'Role.Arn' --output text

# If missing, create it:
aws iam create-service-linked-role \
  --aws-service-name spotfleet.amazonaws.com
```

## Step 1: Create a launch template

```bash
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name spot-fleet-web-server \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m5.large",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0abc123"],
    "IamInstanceProfile": { "Arn": "arn:aws:iam::123456789012:instance-profile/spot-fleet-role" },
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": { "VolumeSize": 30, "VolumeType": "gp3", "DeleteOnTermination": true }
    }]
  }' \
  --query 'LaunchTemplate.LaunchTemplateId' --output text)

echo "Launch Template ID: $LT_ID"
```

## Step 2: Check Spot placement scores (pre-flight)

```bash
aws ec2 get-spot-placement-scores \
  --instance-types m5.large m5a.large c5.large \
  --target-capacity 20 \
  --target-capacity-type vcpu \
  --region us-east-1 \
  --single-availability-zone true
```

## Step 3: Create the Spot Fleet request (maintain + priceCapacityOptimized)

```bash
FLEET_ID=$(aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "Type": "maintain",
    "AllocationStrategy": "priceCapacityOptimized",
    "IamFleetRole": "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet",
    "TargetCapacitySpecification": {
      "TotalTargetCapacity": 20,
      "DefaultTargetCapacityType": "spot",
      "TargetCapacityUnitType": "vcpu"
    },
    "LaunchTemplateConfigs": [{
      "LaunchTemplateSpecification": {
        "LaunchTemplateId": "'"$LT_ID"'",
        "Version": "1"
      },
      "Overrides": [
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1a" },
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1b" },
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1c" },
        { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1a" },
        { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1b" },
        { "InstanceType": "c5.large",  "AvailabilityZone": "us-east-1c" }
      ]
    }],
    "InstanceInterruptionBehavior": "terminate",
    "SpotMaintenanceStrategies": {
      "CapacityRebalance": {
        "ReplacementStrategy": "launch"
      }
    }
  }' \
  --query 'SpotFleetRequestId' --output text)

echo "Spot Fleet Request ID: $FLEET_ID"
```

## Step 4: Monitor fleet status

```bash
# Check fleet request status
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID"

# List instances launched by the fleet
aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id "$FLEET_ID"

# View fleet history (errors, events)
aws ec2 describe-spot-fleet-request-history \
  --spot-fleet-request-id "$FLEET_ID"
```

## Step 5: Modify target capacity (maintain fleets only)

```bash
aws ec2 modify-spot-fleet-request \
  --spot-fleet-request-id "$FLEET_ID" \
  --target-capacity 30 \
  --excess-capacity-termination-policy noTermination
```

## Step 6: Cancel the fleet

```bash
# Terminate all instances and cancel the fleet
aws ec2 cancel-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID" \
  --terminate-instances
```

## Step 7: Spot Fleet with On-Demand Capacity Reservations

```bash
# First, create an ODCR
aws ec2 create-capacity-reservation \
  --instance-type m5.large \
  --instance-platform "Linux/UNIX" \
  --availability-zone us-east-1a \
  --instance-count 3

# Then use it in the Spot Fleet
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "Type": "maintain",
    "AllocationStrategy": "priceCapacityOptimized",
    "IamFleetRole": "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet",
    "TargetCapacitySpecification": {
      "TotalTargetCapacity": 20,
      "OnDemandTargetCapacity": 3,
      "DefaultTargetCapacityType": "spot"
    },
    "OnDemandOptions": {
      "AllocationStrategy": "lowestPrice",
      "CapacityReservationOptions": {
        "UsageStrategy": "use-capacity-reservations-first"
      }
    },
    "LaunchTemplateConfigs": [{
      "LaunchTemplateSpecification": {
        "LaunchTemplateId": "'"$LT_ID"'",
        "Version": "1"
      },
      "Overrides": [
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1a" },
        { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1b" },
        { "InstanceType": "c5.large",  "AvailabilityZone": "us-east-1c" }
      ]
    }],
    "InstanceInterruptionBehavior": "terminate"
  }'
```

## Attribute-based instance selection (InstanceRequirements)

```bash
aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "Type": "maintain",
    "AllocationStrategy": "priceCapacityOptimized",
    "IamFleetRole": "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet",
    "TargetCapacitySpecification": {
      "TotalTargetCapacity": 20,
      "DefaultTargetCapacityType": "spot",
      "TargetCapacityUnitType": "vcpu"
    },
    "LaunchTemplateConfigs": [{
      "LaunchTemplateSpecification": {
        "LaunchTemplateId": "'"$LT_ID"'",
        "Version": "1"
      },
      "Overrides": [
        {
          "InstanceRequirements": {
            "VCpuCount": { "Min": 2, "Max": 4 },
            "MemoryMiB": { "Min": 8192 },
            "AcceleratorCount": { "Max": 0 },
            "BurstablePerformance": "excluded"
          },
          "AvailabilityZone": "us-east-1a"
        },
        {
          "InstanceRequirements": {
            "VCpuCount": { "Min": 2, "Max": 4 },
            "MemoryMiB": { "Min": 8192 },
            "AcceleratorCount": { "Max": 0 },
            "BurstablePerformance": "excluded"
          },
          "AvailabilityZone": "us-east-1b"
        }
      ]
    }],
    "InstanceInterruptionBehavior": "terminate"
  }'
```

## Verification

```bash
# Fleet request state (active, submitted, cancelled, cancelled_running)
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID" \
  --query 'SpotFleetRequestConfigs[0].SpotFleetRequestState'

# Fulfilled vs target capacity
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID" \
  --query 'SpotFleetRequestConfigs[0].ActivityStatus'

# List running fleet instances
aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id "$FLEET_ID" \
  --output table

# Check for fleet errors
aws ec2 describe-spot-fleet-request-history \
  --spot-fleet-request-id "$FLEET_ID" \
  --query 'HistoryRecords[?EventType==`error`]'
```

## Terraform equivalent

```hcl
resource "aws_spot_fleet_request" "web" {
  iam_fleet_role      = "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet"
  spot_price          = "0.10"
  target_capacity     = 20
  allocation_strategy = "priceCapacityOptimized"
  instance_interruption_behavior = "terminate"

  launch_template_config {
    launch_template_specification {
      id      = aws_launch_template.spot.id
      version = "1"
    }

    override {
      instance_type     = "m5.large"
      availability_zone = "us-east-1a"
    }
    override {
      instance_type     = "m5a.large"
      availability_zone = "us-east-1b"
    }
    override {
      instance_type     = "c5.large"
      availability_zone = "us-east-1c"
    }
  }

  depends_on = [aws_launch_template.spot]
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create fleet request | `aws ec2 request-spot-fleet` |
| Describe fleet requests | `aws ec2 describe-spot-fleet-requests` |
| List fleet instances | `aws ec2 describe-spot-fleet-instances` |
| View fleet history | `aws ec2 describe-spot-fleet-request-history` |
| Modify target capacity | `aws ec2 modify-spot-fleet-request` |
| Cancel fleet | `aws ec2 cancel-spot-fleet-requests` |
| Spot placement score | `aws ec2 get-spot-placement-scores` |
| Create launch template | `aws ec2 create-launch-template` |
| Create capacity reservation | `aws ec2 create-capacity-reservation` |
