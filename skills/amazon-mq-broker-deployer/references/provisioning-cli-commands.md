# Provisioning CLI Commands — Amazon MQ Broker Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<broker>`, `<region>`, `<account-id>`, KMS
key ARNs, subnet IDs, security group IDs, configuration ID, LDAP
directory ID, transit gateway ID.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm broker name is available
aws mq describe-broker --broker-id <broker> 2>&1 | head -3

# Confirm CMK exists and is enabled (if encryption at rest with customer CMK)
aws kms describe-key --key-id alias/<alias-name> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm subnet spans >=2 AZs (required for active/standby)
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZ values

# Confirm LDAP directory reachable (if ActiveMQ LDAP auth)
aws ds describe-directories \
  --query 'DirectoryDescriptions[*].[DirectoryId,Name,Type,Stage]' --output text

# Confirm security group exists and has correct ports
aws ec2 describe-security-groups --group-ids <sg-id> \
  --query 'SecurityGroups[0].IpPermissions[*].[FromPort,ToPort,UserIdGroupPairs]' --output text
```

## Step 1: Create the configuration (BEFORE the broker)

### ActiveMQ XML configuration

```bash
# Create the configuration
aws mq create-configuration \
  --configuration-name prod-activemq-config \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0"

# Capture the configuration ID and revision
CONFIG_ID=$(aws mq describe-configuration \
  --configuration-name prod-activemq-config \
  --query 'ConfigurationId' --output text)
echo "Config ID: $CONFIG_ID"

# Update the configuration with XML (base64-encoded)
BROKER_XML=$(cat broker.xml | base64)

aws mq update-configuration \
  --configuration-id "$CONFIG_ID" \
  --configuration-data "$BROKER_XML"
```

### RabbitMQ definitions JSON configuration

```bash
# Create the configuration
aws mq create-configuration \
  --configuration-name prod-rabbit-config \
  --engine-type RABBITMQ \
  --engine-version "3.13"

CONFIG_ID=$(aws mq describe-configuration \
  --configuration-name prod-rabbit-config \
  --query 'ConfigurationId' --output text)

# Update with definitions JSON (base64-encoded)
DEFINITIONS_JSON=$(cat definitions.json | base64)

aws mq update-configuration \
  --configuration-id "$CONFIG_ID" \
  --configuration-data "$DEFINITIONS_JSON"
```

## Step 2: Create the subnet group (must span >=2 AZs for active/standby)

Amazon MQ does not use a named subnet group (unlike ElastiCache).
Instead, you pass subnet IDs directly at broker creation. Verify the
subnets span the required AZs:

```bash
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZs for active/standby
# Expect at least 3 distinct AZs for RabbitMQ cluster
```

## Step 3: Create the security group (correct ports per engine/protocol)

```bash
# ActiveMQ security group — OpenWire (61617), STOMP (61614), MQTT (8883),
# AMQP (5671), WSS (61619), Web Console (8162)
aws ec2 create-security-group \
  --group-name sg-prod-mq \
  --description "Security group for prod ActiveMQ broker" \
  --vpc-id vpc-0abc123

SG_ID=$(aws ec2 describe-security-groups \
  --group-names sg-prod-mq \
  --query 'SecurityGroups[0].GroupId' --output text)

# Allow inbound from application SG
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 61617 \
  --source-security-group-id sg-app456

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 61614 \
  --source-security-group-id sg-app456

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 8883 \
  --source-security-group-id sg-app456

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 8162 \
  --source-security-group-id sg-app456
```

```bash
# RabbitMQ security group — AMQP (5671), Management (15671)
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 5671 \
  --source-security-group-id sg-app456

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 15671 \
  --source-security-group-id sg-app456
```

## Step 4: Create the broker (ActiveMQ active/standby)

```bash
aws mq create-broker \
  --broker-name prod-mq \
  --broker-instance-type mq.m5.large \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --deployment-mode ACTIVE_STANDBY_MULTI_AZ \
  --subnet-ids subnet-0aaa subnet-0bbb \
  --security-groups sg-mq123 \
  --storage-type ebs \
  --ebs-volume-size 200 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-mq-kms \
  --configuration-id "$CONFIG_ID" \
  --configuration-revision 1 \
  --users Username=admin,Password=SecurePass123,ConsoleAccess=true,Groups=admin \
  --logs General=true,Audit=true \
  --auto-minor-version-upgrade true \
  --maintenance-window-start-time \
    DayOfWeek=SUNDAY,TimeOfDay=03:00,TimeZone=UTC \
  --tags Environment=production,Workload=messaging
```

## Step 5: Create the broker (RabbitMQ cluster with IAM auth)

```bash
aws mq create-broker \
  --broker-name prod-rabbit \
  --broker-instance-type mq.m5.2xlarge \
  --engine-type RABBITMQ \
  --engine-version "3.13" \
  --deployment-mode CLUSTER_MULTI_AZ \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --security-groups sg-rabbit \
  --storage-type ebs \
  --ebs-volume-size 200 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/rabbit-kms \
  --configuration-id "$CONFIG_ID" \
  --configuration-revision 1 \
  --authentication-strategy ldap \
  --logs General=true,Audit=true \
  --auto-minor-version-upgrade true \
  --tags Environment=production,Workload=messaging
```

## Step 6: Wait for the broker to become available

```bash
# Poll the broker state
aws mq describe-broker --broker-id prod-mq \
  --query 'BrokerState'

# Wait for "RUNNING" (creation takes 10-15 minutes for active/standby)
# The broker transitions: CREATION_IN_PROGRESS → RUNNING
```

## Step 7: Transit gateway cross-account (RabbitMQ)

```bash
# Share the transit gateway with the consuming account
aws ram create-resource-share \
  --name mq-tgw-share \
  --resource-arns arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-0abc123 \
  --principals 123456789012

# In the consuming account (123456789012): accept the RAM invitation
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn <invitation-arn>

# Configure TGW route table for cross-VPC routing
aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id tgw-rtb-0abc \
  --transit-gateway-attachment-id tgw-attach-0aaa

aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id tgw-rtb-0abc \
  --destination-cidr-block 10.10.0.0/16 \
  --transit-gateway-attachment-id tgw-attach-0bbb
```

## Step 8: Post-deployment verification

```bash
# Broker state, endpoints, encryption, logs, configuration
aws mq describe-broker --broker-id prod-mq

# Configuration details (revision, data)
aws mq describe-configuration --configuration-id <config-id>

# Security group rules
aws ec2 describe-security-groups --group-ids sg-mq123

# KMS key state
aws kms describe-key --key-id alias/prod-mq-kms

# LDAP directory state (if ActiveMQ LDAP auth)
aws ds describe-directories \
  --query 'DirectoryDescriptions[*].[DirectoryId,Name,Stage]' --output text

# CloudWatch log groups
aws logs describe-log-groups \
  --log-group-name-prefix /aws/amazonmq/broker/prod-mq \
  --query 'logGroups[*].logGroupName' --output text
```
