# Security, Encryption, and CloudWatch Monitoring — MQ Broker Deployer

Deep reference on encryption (at-rest with KMS, in-transit with TLS),
authentication (LDAP for ActiveMQ, IAM for RabbitMQ, mTLS, basic auth),
security group configuration per protocol, and CloudWatch alarm
configuration for broker metrics. Loaded on demand by the skill.

## Encryption

### At-rest encryption (KMS)

Amazon MQ encrypts broker storage (EBS volumes) at rest. The encryption
key can be:

- **AWS-owned key:** default, no management overhead, but no audit or
  rotation control. NOT recommended for production.
- **Customer-managed CMK:** you control the key policy, rotation, and
  access. Recommended for production.

**Set at broker creation — cannot be changed later.**

```bash
# Create broker with customer-managed CMK
aws mq create-broker \
  --broker-name prod-mq \
  --engine-type ActiveMQ \
  --engine-version 5.18.0 \
  --host-instance-type mq.m5.large \
  --deployment-mode ACTIVE_STANDBY \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-groups sg-mq123 \
  --encryption-options '{"UseAwsOwnedKey": false, "KmsKeyId": "alias/prod-mq-kms"}'
```

**KMS key policy must permit the Amazon MQ service principal:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "mq.amazonaws.com"
      },
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

### In-transit encryption (TLS)

TLS is enabled by default on all Amazon MQ brokers. Broker endpoints
use TLS-secured ports:

```text
ActiveMQ TLS ports:
  OpenWire (SSL):   61617
  AMQP (SSL):       5671
  STOMP (SSL):      61614
  MQTT (SSL):       8883
  WebSocket (SSL):  61619
  Web Console:      8162

RabbitMQ TLS ports:
  AMQP (SSL):       5671
  STOMP (SSL):      61614
  MQTT (SSL):       8883
  Management UI:    15671
```

Disabling TLS is NOT recommended. All production brokers must use TLS.

## Authentication

### Basic authentication

Both ActiveMQ and RabbitMQ support basic username/password auth.
Credentials are set at broker creation and stored in AWS Secrets
Manager.

```bash
aws mq create-broker \
  --broker-name dev-mq \
  --engine-type ActiveMQ \
  --users '[{"Username": "admin", "Password": "<from-secrets-manager>", "ConsoleAccess": true, "Groups": ["admin"]}]'
```

**Limitations:** no central identity, no per-user rotation, no per-user
audit. OK for dev/test, not for production.

### LDAP authentication (ActiveMQ)

ActiveMQ can authenticate against an external LDAP directory (Active
Directory, OpenLDAP). Configured via broker configuration XML override.

**Prerequisites:**
- LDAP server reachable from the broker VPC (ports 389/636).
- Security group outbound rules permit broker-to-LDAP traffic.
- LDAP service account credentials stored in Secrets Manager.

**Configuration XML (LdapLoginModule):**

```xml
<bean class="org.apache.activemq.security.JaasStandaloneLoginModule">
  <property name="loginModule" value="org.apache.activemq.jaas.LdapLoginModule"/>
  <property name="options">
    <map>
      <entry key="initialContextFactory" value="com.sun.jndi.ldap.LdapCtxFactory"/>
      <entry key="connectionURL" value="ldaps://d-1234567890.directory.example.com:636"/>
      <entry key="connectionUsername" value="CN=admin,OU=Users,DC=example,DC=com"/>
      <entry key="connectionPassword" value="${LDAP_PASSWORD}"/>
      <entry key="userBase" value="OU=Users,DC=example,DC=com"/>
      <entry key="userRoleName" value="cn"/>
      <entry key="userSearchMatching" value="(sAMAccountName={0})"/>
      <entry key="userSearchSubtree" value="true"/>
    </map>
  </property>
</bean>
```

### IAM authentication (RabbitMQ)

RabbitMQ supports AWS IAM-based authentication. Counterintuitively, this
is enabled by setting `authenticationStrategy = LDAP` on the broker
(this strategy name enables IAM for RabbitMQ, not LDAP).

```bash
aws mq create-broker \
  --broker-name prod-rmq \
  --engine-type RabbitMQ \
  --authentication-strategy LDAP
```

**IAM policy for RabbitMQ broker access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mq:Connect",
        "mq:CreateTag",
        "mq:DescribeUser"
      ],
      "Resource": "arn:aws:mq:us-east-1:123456789012:broker:prod-rmq:b-0001-0000-0000-0000-000000000000"
    }
  ]
}
```

## Security group configuration

Each protocol uses a specific port. The security group must allow
inbound traffic on all ports for protocols in use.

```bash
# ActiveMQ security group (OpenWire + AMQP + Console)
aws ec2 create-security-group \
  --group-name mq-activemq-sg \
  --description "ActiveMQ broker security group" \
  --vpc-id vpc-aaa11122

aws ec2 authorize-security-group-ingress \
  --group-id sg-mq123 \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=61617,ToPort=61617,IpRanges=[{CidrIp=10.0.0.0/16}]" \
    "IpProtocol=tcp,FromPort=5671,ToPort=5671,IpRanges=[{CidrIp=10.0.0.0/16}]" \
    "IpProtocol=tcp,FromPort=8162,ToPort=8162,IpRanges=[{CidrIp=10.0.0.0/16}]"

# RabbitMQ security group (AMQP + STOMP)
aws ec2 authorize-security-group-ingress \
  --group-id sg-rmq456 \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=5671,ToPort=5671,IpRanges=[{CidrIp=10.0.0.0/16}]" \
    "IpProtocol=tcp,FromPort=61614,ToPort=61614,IpRanges=[{CidrIp=10.0.0.0/16}]"
```

For cross-VPC access, use VPC peering, Transit Gateway, or a managed
prefix list for the client CIDR.

## CloudWatch monitoring

### Broker metrics

Amazon MQ emits metrics to the `AWS/AmazonMQ` CloudWatch namespace
automatically. Key metrics:

| Metric | Dimensions | Description |
|---|---|---|
| CpuUtilization | Broker | Broker CPU utilization (%) |
| MemoryUtilization | Broker | Broker memory (JVM heap) utilization (%) |
| EnqueueCount | Broker, Queue | Messages enqueued per second |
| DequeueCount | Broker, Queue | Messages dequeued per second |
| QueueSize | Broker, Queue | Current queue depth |
| TotalConsumerCount | Broker | Active consumers connected |
| TotalProducerCount | Broker | Active producers connected |
| BrokerCommitCount | Broker | Transaction commits (ActiveMQ) |

### Recommended alarms

```bash
# CPU alarm (threshold: 80% for 5 min)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-high-cpu" \
  --metric-name CpuUtilization \
  --namespace AWS/AmazonMQ \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"

# Memory alarm (threshold: 80% for 5 min)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-high-memory" \
  --metric-name MemoryUtilization \
  --namespace AWS/AmazonMQ \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"

# Enqueue drop alarm (threshold: <1 msg in 10 min)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-no-enqueues" \
  --metric-name EnqueueCount \
  --namespace AWS/AmazonMQ \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"

# Queue size growth alarm (threshold: >10,000 for 15 min)
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-backlog" \
  --metric-name QueueSize \
  --namespace AWS/AmazonMQ \
  --statistic Maximum \
  --period 300 \
  --threshold 10000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"
```

### SNS topic for alarm notifications

```bash
aws sns create-topic --name mq-alerts
aws sns subscribe \
  --topic-arn "arn:aws:sns:us-east-1:123456789012:mq-alerts" \
  --protocol email \
  --notification-endpoint oncall@example.com
```
