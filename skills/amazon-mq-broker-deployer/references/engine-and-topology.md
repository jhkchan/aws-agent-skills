# Engine and Topology Guide — Amazon MQ Broker Deployer

Deep reference on ActiveMQ-vs-RabbitMQ feature tradeoffs, deployment
mode mechanics (single instance, active/standby, cluster), failover
semantics, authentication interactions (LDAP, IAM, mTLS), configuration
formats (XML vs definitions JSON), and transit gateway cross-account
topology. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## ActiveMQ vs RabbitMQ — full feature matrix

The single highest-impact Amazon MQ decision is the engine. It is
**immutable** without a full application client rewrite (different
protocol APIs and topology models) plus a drain-and-replay window.

| Feature / property | ActiveMQ | RabbitMQ |
|---|---|---|
| Protocols | OpenWire, STOMP, MQTT, AMQP 1.0, WS | AMQP 0-9-1, AMQP 1.0, MQTT, STOMP |
| Topology model | Queues, Topics, Virtual Topics, Durable Subscribers | Exchanges (direct, fanout, topic, headers) + Queues + Bindings |
| HA mode | Active/Standby (shared EBS) | Active/Standby OR Cluster (3+ nodes, quorum) |
| Horizontal scaling | NO (single active instance) | YES (cluster mode, 3+ nodes) |
| Encryption at rest | YES (KMS, AWS-managed or CMK) | YES (KMS, AWS-managed or CMK) |
| Encryption in transit (TLS) | YES | YES |
| AWS IAM authentication | NO | YES (creation-time-only) |
| LDAP authentication | YES (JAAS LDAPLoginModule) | YES (via rabbitmq-auth-backend-ldap) |
| Mutual TLS (client cert) | YES | YES |
| JMS support | YES (native) | NO (via plugin, limited) |
| Virtual Topics | YES | NO |
| Exchange types | NO (destinations only) | YES (direct, fanout, topic, headers) |
| Quorum queues | NO | YES (RabbitMQ 3.8+) |
| Streams | NO | YES (RabbitMQ 3.9+) |
| Audit logging | YES (CloudWatch) | YES (CloudWatch) |
| Automatic minor version upgrades | YES (default on) | YES (default on) |
| Web management console | YES (ActiveMQ Web Console, port 8162) | YES (RabbitMQ Management, port 15671) |

**Decision rule (when in doubt):** pick ActiveMQ if the workload needs
JMS, OpenWire, or virtual topics. Pick RabbitMQ if the workload needs
AMQP 0-9-1 exchanges, AWS IAM authentication, or horizontal scaling via
cluster mode. For greenfield multi-protocol workloads where either
could work, ActiveMQ has the broader protocol surface (5 protocols vs
RabbitMQ's 4).

## Deployment mode mechanics

### Single instance (SINGLE_INSTANCE)

- 1 broker, no failover, EBS-backed persistence.
- Messages survive broker restart (stored on EBS).
- No standby — a broker failure = downtime until Amazon MQ restarts it
  (minutes).
- Use for dev/test or workloads tolerating downtime.

### Active/Standby (ACTIVE_STANDBY_MULTI_AZ)

- 1 active broker + 1 standby in a different AZ.
- Shared EBS storage — the standby does NOT accept connections.
- ActiveMQ failover: Amazon MQ promotes the EBS volume to the standby
  (5-15 minutes).
- RabbitMQ failover: similar shared-storage promotion.
- Clients must use failover-aware connection URIs:
  - ActiveMQ: `failover:(ssl://broker-url:61617)`
  - RabbitMQ: client library handles reconnect with multiple host entries.
- Data loss: messages not yet persisted to EBS are LOST.

### Cluster (CLUSTER_MULTI_AZ) — RabbitMQ only

- 3+ nodes (quorum requirement — 2-node cluster does NOT work).
- Nodes in different AZs for HA.
- Quorum queues: automatic leader election (10-30 seconds).
- Horizontal scaling: connections distribute across nodes.
- Tolerates N/2 - 1 node failures (3-node tolerates 1, 5-node
  tolerates 2).
- Going from active/standby → cluster REQUIRES broker deletion +
  recreation.

## Failover semantics in detail

### ActiveMQ active/standby failover

```
Active broker (AZ-a)          Standby broker (AZ-b)
     │                              │
     ├── accepts all connections    │ (NO connections accepted)
     ├── writes to shared EBS ──────┤ (shared EBS volume)
     │                              │
  === FAILURE (AZ-a) ===            │
     ✗                              │
                                    ├── Amazon MQ detaches EBS from AZ-a
                                    ├── Attaches EBS to AZ-b standby
                                    ├── Starts broker process
                                    └── Promotes to active (5-15 min)
```

- Clients using `failover:(ssl://...)` URI automatically reconnect.
- Plain TCP clients will NOT fail over — they time out and error.
- The broker's `BrokerInstance` URL array includes both endpoints;
  the ActiveMQ client failover transport tries each in order.

### RabbitMQ cluster quorum

```
Node 1 (AZ-a)    Node 2 (AZ-b)    Node 3 (AZ-c)
     │                 │                 │
     ├── quorum queue  ├── quorum queue  ├── quorum queue
     │   (leader)      │   (follower)    │   (follower)
     │                 │                 │
  === FAILURE (AZ-a) ===                  │
     ✗                 │                 │
                       ├── detects leader loss
                       ├── quorum election (2 of 3 alive)
                       └── Node 2 promoted to leader (10-30 sec)
```

- Quorum queues replicate data across the quorum majority.
- Classic mirrored queues also provide HA but are being deprecated in
  favor of quorum queues.
- Streams (RabbitMQ 3.9+) provide append-only log semantics.

## Authentication interactions

| Feature | ActiveMQ | RabbitMQ |
|---|---|---|
| Username/password (basic) | YES (`--users`) | YES (`--users`) |
| LDAP | YES (JAAS LDAPLoginModule in broker.xml) | YES (rabbitmq-auth-backend-ldap plugin) |
| AWS IAM | NO | YES (creation-time-only; SigV4) |
| Mutual TLS | YES (client cert in TLS handshake) | YES (client cert in TLS handshake) |

**IAM auth for RabbitMQ (critical detail):**
- Enabled at broker creation via the authentication strategy.
- AWS principals (IAM users, roles) connect using SigV4-signed
  credentials — no password needed.
- The broker's IAM policy maps IAM principals to RabbitMQ permissions.
- **Creation-time-only:** a broker created with basic auth CANNOT be
  converted to IAM auth without deleting and recreating the broker.
- Use when the workload is AWS-native (Lambda, ECS, EKS) and wants to
  eliminate password management.

**LDAP for ActiveMQ:**
- Configured in broker.xml via the JAAS LDAPLoginModule.
- Requires a reachable directory service (AWS Managed Microsoft AD,
  Simple AD, or on-prem AD via Direct Connect/VPN).
- The directory must be in the same VPC or reachable via peering/TGW.
- User groups map to ActiveMQ broker groups for authorization.

## Configuration formats

### ActiveMQ XML (broker.xml)

ActiveMQ uses an XML configuration file for destinations, plugins,
transport connectors, and destination policies.

```xml
<broker xmlns="http://activemq.apache.org/schema/core"
        brokerName="prod-mq"
        useJmx="true"
        advisorySupport="false">

  <!-- Transport connectors: enable protocols -->
  <transportConnectors>
    <transportConnector name="openwire" uri="ssl://0.0.0.0:61617"/>
    <transportConnector name="amqp" uri="amqp+ssl://0.0.0.0:5671"/>
    <transportConnector name="stomp" uri="stomp+ssl://0.0.0.0:61614"/>
    <transportConnector name="mqtt" uri="ssl+mqtt://0.0.0.0:8883"/>
    <transportConnector name="ws" uri="wss://0.0.0.0:61619"/>
  </transportConnectors>

  <!-- Destination policies -->
  <destinationPolicy>
    <policyMap>
      <policyEntries>
        <policyEntry queue=">" producerFlowControl="true"
                     memoryLimit="512mb"/>
        <policyEntry topic=">" producerFlowControl="true"
                     memoryLimit="512mb">
          <pendingSubscriberPolicy>
            <vmCursor/>
          </pendingSubscriberPolicy>
        </policyEntry>
      </policyEntries>
    </policyMap>
  </destinationPolicy>

  <!-- LDAP authentication (JAAS) -->
  <plugins>
    <jaasAuthenticationPlugin configuration="ldap" />
  </plugins>
</broker>
```

### RabbitMQ definitions JSON

RabbitMQ uses a definitions JSON for exchanges, queues, bindings,
users, and permissions.

```json
{
  "vhosts": [{"name": "/"}],
  "users": [
    {"name": "producer", "password_hash": "...", "hashing_algorithm": "rabbit_password_hashing_sha256", "tags": ""}
  ],
  "permissions": [
    {"user": "producer", "vhost": "/", "configure": ".*", "write": ".*", "read": ".*"}
  ],
  "exchanges": [
    {"name": "orders", "vhost": "/", "type": "topic", "durable": true, "auto_delete": false, "internal": false, "arguments": {}}
  ],
  "queues": [
    {"name": "order-processor", "vhost": "/", "durable": true, "auto_delete": false, "arguments": {"x-queue-type": "quorum"}}
  ],
  "bindings": [
    {"source": "orders", "vhost": "/", "destination": "order-processor", "destination_type": "queue", "routing_key": "order.#", "arguments": {}}
  ]
}
```

## Transit gateway cross-account topology

For RabbitMQ brokers accessed across AWS accounts via Transit Gateway:

```
Account A (123456789012)           Account B (123456789012)
┌─────────────────────────┐       ┌─────────────────────────┐
│  VPC-A (10.10.0.0/16)   │       │  VPC-B (10.20.0.0/16)   │
│  ┌───────────────────┐  │       │  ┌───────────────────┐  │
│  │ RabbitMQ broker   │  │       │  │ Consumer app      │  │
│  │ shared-rabbit     │  │       │  │ (ECS / Lambda)    │  │
│  │ sg-shared-rabbit  │  │       │  │ sg-app            │  │
│  └────────┬──────────┘  │       │  └────────┬──────────┘  │
│           │             │       │           │             │
│  TGW Attachment-A ──────┼───┐   └─── TGW Attachment-B ────┤
└─────────────────────────┘   │       └─────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │ Transit Gateway    │
                    │ tgw-0abc123        │
                    │ (shared via RAM    │
                    │  to Account B)     │
                    └────────────────────┘
```

**Provisioning sequence:**
1. Create the Transit Gateway in Account A.
2. Create TGW attachments for VPC-A and VPC-B.
3. Configure TGW route tables (VPC-A ↔ VPC-B).
4. Share the TGW to Account B via RAM
   (`aws ram create-resource-share`).
5. Accept the RAM invitation in Account B.
6. Configure security group rules:
   - sg-shared-rabbit: inbound 5671 from sg-app (Account A) AND from
     10.20.0.0/16 (Account B VPC CIDR).
7. Create the RabbitMQ broker in VPC-A.
8. Consumers in VPC-B connect to the broker's AMQP endpoint over the
   TGW.

## AWS documentation references

- Amazon MQ Developer Guide — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html
- ActiveMQ Configuration — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/activemq-configuration-settings.html
- RabbitMQ Configuration — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/rabbitmq-configuration-settings.html
- Amazon MQ Best Practices — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-best-practices.html
- Amazon MQ Authentication — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-authentication.html
- RabbitMQ IAM Auth — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/rabbitmq-iam-authentication.html
- Transit Gateway — https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html
