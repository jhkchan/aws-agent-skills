# Engine Selection and Deployment Topology — MQ Broker Deployer

Deep reference on ActiveMQ vs RabbitMQ engine selection, deployment
mode constraints (single-instance, active/standby, cluster), AZ and
subnet count requirements, failover behavior, and throughput scaling.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Engine selection matrix

### ActiveMQ

- **Protocols:** OpenWire (native JMS), AMQP 1.0, STOMP 1.2, MQTT 3.1,
  WebSocket (WS).
- **HA modes:** Single-Instance, Active/Standby.
- **Configuration:** XML-based (`broker.xml` overrides via Amazon MQ
  configuration).
- **Best for:** Java/JMS applications, legacy integration requiring
  OpenWire, multi-protocol workloads (STOMP + MQTT + AMQP), when
  JMS-compliant messaging is required.

### RabbitMQ

- **Protocols:** AMQP 0-9-1 (native), MQTT 3.1.1, STOMP 1.2.
- **HA modes:** Single-Instance, Cluster (3 brokers).
- **Configuration:** Definitions JSON, exchange/queue declarations.
- **Best for:** High-throughput AMQP workloads, microservices
  messaging, when horizontal scaling is needed, event-driven
  architectures.

### Decision heuristic

```text
Do you need horizontal scale (throughput scales with broker count)?
  ├── YES → RabbitMQ cluster (only engine with cluster mode)
  └── NO → Do you need JMS/OpenWire?
            ├── YES → ActiveMQ (single or active/standby)
            └── NO → Either engine works.
                     ActiveMQ active/standby: warm standby, no scale.
                     RabbitMQ cluster: all active, quorum queues.
```

## Deployment mode detail

### Single-Instance

- **Brokers:** 1.
- **AZs:** 1.
- **HA:** None. AZ or broker failure = broker unavailable.
- **Subnet requirement:** 1 subnet in 1 AZ.
- **Use case:** Development, testing, non-critical workloads.
- **Cost:** Lowest (1 broker instance).

### Active/Standby (ActiveMQ only)

- **Brokers:** 2. One active (primary), one standby (warm replica).
- **AZs:** 2 (each broker in a different AZ).
- **HA:** Yes. Automatic failover from active to standby on active
  failure.
- **Failover behavior:**
  - The active broker handles all traffic. The standby is warm — it
    replicates state via shared EBS storage but does NOT serve client
    traffic.
  - On active failure, the standby is promoted. Clients reconnect to
    the new active endpoint (Amazon MQ updates the DNS CNAME).
  - Failover time: typically 5-15 minutes (EBS re-attachment + broker
    startup).
- **Subnet requirement:** Exactly 2 subnets in 2 different AZs.
- **Throughput:** Same as single broker (standby does not add
  capacity).
- **Use case:** Production HA without horizontal scaling.

### Cluster (RabbitMQ only)

- **Brokers:** 3. All active.
- **AZs:** 3 (each broker in a different AZ).
- **HA:** Yes. Quorum queues (Raft consensus) replicate across all 3
  brokers.
- **Failover behavior:**
  - All 3 brokers serve traffic simultaneously.
  - Quorum queues maintain a Raft consensus group. If one broker
    fails, the remaining 2 continue (quorum = 2 of 3).
  - No failover time — the other brokers are already active.
- **Subnet requirement:** Exactly 3 subnets in 3 different AZs.
- **Throughput:** Scales with broker count. Adding more consumers
  across brokers increases aggregate throughput.
- **Use case:** Production HA with horizontal scaling, high-throughput
  workloads.

## AZ and subnet count validation

Amazon MQ validates the subnet count against the deployment mode at
broker creation. The API call fails immediately if the count is wrong.

```text
Deployment mode       | Required subnets | Required AZs
--------------------- | ---------------- | ------------
SINGLE_INSTANCE       | 1                | 1
ACTIVE_STANDBY        | 2                | 2 (must differ)
CLUSTER_MULTI_AZ      | 3                | 3 (must differ)
```

**Validation command before creating the broker:**

```bash
# Verify subnets are in different AZs
aws ec2 describe-subnets \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}' \
  --output table

# Ensure all AZs are different
# If any two subnets share an AZ, the broker creation will fail
```

## Throughput scaling comparison

### ActiveMQ active/standby

Throughput is capped by a single broker's capacity:

```text
mq.m5.large active/standby:
  Active broker: mq.m5.large capacity (~5,000 msg/sec for 1KB messages)
  Standby broker: mq.m5.large (warm, not serving traffic)
  Aggregate throughput: ~5,000 msg/sec (does NOT double)
```

### RabbitMQ cluster

Throughput scales with broker count:

```text
mq.m5.large cluster (3 brokers):
  Broker 1: mq.m5.large (~5,000 msg/sec)
  Broker 2: mq.m5.large (~5,000 msg/sec)
  Broker 3: mq.m5.large (~5,000 msg/sec)
  Aggregate throughput: ~15,000 msg/sec (scales with consumer distribution)

Note: quorum queue throughput per queue is limited by the Raft leader.
To scale, use multiple quorum queues distributed across brokers.
```

## Terraform examples

### ActiveMQ active/standby

```hcl
resource "aws_mq_broker" "activemq" {
  broker_name        = "prod-mq"
  engine_type        = "ActiveMQ"
  engine_version     = "5.18.0"
  host_instance_type = "mq.m5.large"
  deployment_mode    = "ACTIVE_STANDBY"

  subnet_ids         = ["subnet-aaa", "subnet-bbb"]
  security_groups    = ["sg-mq123"]

  encryption_options {
    use_aws_owned_key = false
    kms_key_id        = aws_kms_key.mq.arn
  }

  maintenance_window_start_time {
    day_of_week = "SUNDAY"
    time_of_day = "03:00"
    time_zone   = "UTC"
  }

  auto_minor_version_upgrade = true

  user {
    username = "admin"
    password = data.aws_secretsmanager_secret_version.mq_password.secret_string
  }

  configuration {
    id       = aws_mq_configuration.activemq_ldap.id
    revision = aws_mq_configuration.activemq_ldap.latest_revision
  }

  tags = {
    Environment = "production"
  }
}
```

### RabbitMQ cluster

```hcl
resource "aws_mq_broker" "rabbitmq" {
  broker_name             = "prod-rmq"
  engine_type             = "RabbitMQ"
  engine_version          = "3.13.2"
  host_instance_type      = "mq.m5.large"
  deployment_mode         = "CLUSTER_MULTI_AZ"
  authentication_strategy = "LDAP"  # enables IAM auth for RabbitMQ

  subnet_ids         = ["subnet-aaa", "subnet-bbb", "subnet-ccc"]
  security_groups    = ["sg-rmq456"]

  encryption_options {
    use_aws_owned_key = false
    kms_key_id        = aws_kms_key.rmq.arn
  }

  auto_minor_version_upgrade = true

  tags = {
    Environment = "production"
    Engine      = "rabbitmq"
  }
}
```
