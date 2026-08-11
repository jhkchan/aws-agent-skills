# Provisioning CLI Commands — EC2 Launch Template Deployer

Full copy-pasteable CLI command sequence for provisioning EC2 Launch
Templates with AMI validation, block device mapping, network
interfaces, IMDSv2, tag specifications, and capacity reservation
targeting. Variables to substitute: `<region>`, `<account-id>`,
`<ami-id>`, `<lt-id>`, `<instance-type>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Validate AMI exists and check architecture
AMI_ID=ami-0abcdef1234567890
AMI_ARCH=$(aws ec2 describe-images --image-ids "$AMI_ID" \
  --query 'Images[0].Architecture' --output text)
echo "AMI Architecture: $AMI_ARCH"

# Validate instance type is available in the region
INSTANCE_TYPE=m7g.large
aws ec2 describe-instance-type-offerings \
  --location-type availability-zone \
  --filters Name=instance-type,Values="$INSTANCE_TYPE" \
  --query 'InstanceTypeOfferings[*].Location' --output text

# Validate key pair exists
aws ec2 describe-key-pairs --key-names prod-graviton-key

# Validate IAM instance profile has a role
aws iam describe-instance-profiles \
  --instance-profile-name web-server-role \
  --query 'InstanceProfiles[0].Roles[0].RoleName' --output text

# Validate security groups are in the target VPC
aws ec2 describe-security-groups --group-ids sg-0abc123 sg-0def456 \
  --query 'SecurityGroups[*].[GroupId,VpcId]' --output text

# Validate subnet is in the same VPC as the SGs
aws ec2 describe-subnets --subnet-ids subnet-0abc123def456 \
  --query 'Subnets[0].[SubnetId,VpcId]' --output text
```

## Step 1: Create a launch template (Graviton + IMDSv2 + gp3 + tags)

```bash
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name graviton-web-server \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m7g.large",
    "KeyName": "prod-graviton-key",
    "IamInstanceProfile": {
      "Arn": "arn:aws:iam::123456789012:instance-profile/web-server-role"
    },
    "UserData": "'"$(base64 user-data.sh | tr -d '\n')"'",
    "BlockDeviceMappings": [
      {
        "DeviceName": "/dev/xvda",
        "Ebs": {
          "VolumeSize": 30,
          "VolumeType": "gp3",
          "Iops": 3000,
          "Throughput": 125,
          "DeleteOnTermination": true,
          "Encrypted": true
        }
      },
      {
        "DeviceName": "/dev/xvdb",
        "Ebs": {
          "VolumeSize": 100,
          "VolumeType": "gp3",
          "Iops": 6000,
          "Throughput": 250,
          "DeleteOnTermination": true,
          "Encrypted": true
        }
      }
    ],
    "NetworkInterfaces": [
      {
        "DeviceIndex": 0,
        "SubnetId": "subnet-0abc123def456",
        "Groups": ["sg-0abc123", "sg-0def456"],
        "AssociatePublicIpAddress": true,
        "Ipv6AddressCount": 1
      }
    ],
    "MetadataOptions": {
      "HttpEndpoint": "enabled",
      "HttpTokens": "required",
      "HttpPutResponseHopLimit": 2,
      "InstanceMetadataTags": "enabled"
    },
    "TagSpecifications": [
      {
        "ResourceType": "instance",
        "Tags": [
          { "Key": "Name", "Value": "graviton-web-server" },
          { "Key": "Environment", "Value": "production" },
          { "Key": "Application", "Value": "checkout-service" }
        ]
      },
      {
        "ResourceType": "volume",
        "Tags": [
          { "Key": "Name", "Value": "graviton-web-root" },
          { "Key": "Environment", "Value": "production" }
        ]
      },
      {
        "ResourceType": "network-interface",
        "Tags": [
          { "Key": "Name", "Value": "graviton-web-eni-0" }
        ]
      }
    ]
  }' \
  --query 'LaunchTemplate.LaunchTemplateId' --output text)

echo "Launch Template ID: $LT_ID"
```

## Step 2: Create a new version (e.g., update AMI)

```bash
aws ec2 create-launch-template-version \
  --launch-template-id "$LT_ID" \
  --launch-template-data '{
    "ImageId": "ami-0newami1234567890",
    "InstanceType": "m7g.large"
  }'

# Set the new version as default
aws ec2 modify-launch-template \
  --launch-template-id "$LT_ID" \
  --default-version 2
```

## Step 3: Capacity reservation targeting

```bash
# Verify the reservation exists and matches
aws ec2 describe-capacity-reservations \
  --capacity-reservation-ids cr-0abc123def456 \
  --query 'CapacityReservations[0].[State,InstanceType,AvailabilityZone,InstancePlatform]' --output text

# Create a launch template with targeted capacity reservation
aws ec2 create-launch-template \
  --launch-template-name targeted-reservation-web \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "c7i.large",
    "CapacityReservationSpecification": {
      "CapacityReservationTarget": {
        "CapacityReservationIds": ["cr-0abc123def456"]
      }
    }
  }'
```

## Step 4: Launch an instance from the template

```bash
INSTANCE_ID=$(aws ec2 run-instances \
  --launch-template "LaunchTemplateId=$LT_ID,Version=1" \
  --count 1 \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance ID: $INSTANCE_ID"
```

## Step 5: Verification

```bash
# Template metadata
aws ec2 describe-launch-templates --launch-template-ids "$LT_ID"

# All versions
aws ec2 describe-launch-template-versions --launch-template-id "$LT_ID"

# Specific version (verify IMDSv2, block devices, tags)
aws ec2 describe-launch-template-versions \
  --launch-template-id "$LT_ID" \
  --versions 1 \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.[MetadataOptions,BlockDeviceMappings,TagSpecifications]'

# Verify the launched instance has IMDSv2 enforced
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].MetadataOptions' --output table

# Verify block devices on the instance
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings' --output table
```

## Terraform equivalent

```hcl
resource "aws_launch_template" "web" {
  name          = "graviton-web-server"
  image_id      = "ami-0abcdef1234567890"
  instance_type = "m7g.large"
  key_name      = "prod-graviton-key"

  iam_instance_profile {
    arn = "arn:aws:iam::123456789012:instance-profile/web-server-role"
  }

  user_data = base64encode(file("user-data.sh"))

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      iops                  = 3000
      throughput            = 125
      delete_on_termination = true
      encrypted             = true
    }
  }

  network_interfaces {
    device_index                = 0
    subnet_id                   = "subnet-0abc123def456"
    security_groups             = ["sg-0abc123", "sg-0def456"]
    associate_public_ip_address = true
    ipv6_address_count          = 1
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
    instance_metadata_tags      = "enabled"
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "graviton-web-server"
      Environment = "production"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name = "graviton-web-root"
    }
  }

  capacity_reservation_specification {
    capacity_reservation_target {
      capacity_reservation_id = "cr-0abc123def456"
    }
  }
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create launch template | `aws ec2 create-launch-template` |
| Create new version | `aws ec2 create-launch-template-version` |
| Set default version | `aws ec2 modify-launch-template` |
| Describe templates | `aws ec2 describe-launch-templates` |
| Describe versions | `aws ec2 describe-launch-template-versions` |
| Delete template | `aws ec2 delete-launch-template` |
| Launch instance from template | `aws ec2 run-instances --launch-template` |
| Describe capacity reservations | `aws ec2 describe-capacity-reservations` |
| Validate AMI architecture | `aws ec2 describe-images --image-ids` |
| Check instance type availability | `aws ec2 describe-instance-type-offerings` |
