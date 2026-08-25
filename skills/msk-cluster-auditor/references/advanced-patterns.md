# Advanced Patterns — MSK Cluster Auditor

## Step 0: Expert knowledge — non-obvious MSK behaviors that change classification

Each behavior below changes a verdict if ignored:

- **`TLS_PLAINTEXT` is NOT "TLS with a plaintext fallback."** It is a
  dual-mode listener that publishes BOTH a TLS port and a plaintext port.
  Clients can choose either — the plaintext path carries every message
  unencrypted. Classify `TLS_PLAINTEXT` as **NO_ENCRYPTION**, not
  CONFIG_GAP. The encryption guarantee is broken the moment a plaintext
  path exists. A client connecting over plaintext bypasses TLS entirely;
  there is no downgrade negotiation, just two open doors.

- **`InClusterEncryption` is independent of `ClientBroker`.**
  `ClientBroker: TLS` encrypts client-to-broker traffic.
  `InClusterEncryption: true` encrypts broker-to-broker (inter-broker)
  traffic. A cluster with `ClientBroker: TLS` + `InClusterEncryption:
  false` encrypts the client wire but sends data in plaintext between
  brokers (often cross-AZ). Flag missing `InClusterEncryption` as a
  CONFIG_GAP finding — it does NOT rise to NO_ENCRYPTION because the
  client wire is still encrypted.

- **MSK always encrypts data volumes at rest.** There is no
  "unencrypted at rest" state — the `EncryptionAtRest` field, if present,
  names the KMS key; if absent, MSK uses an AWS-managed CMK
  (`alias/aws/kafka`). The audit question is governance, not presence:
  a customer-managed key gives you rotation control, key-policy audit,
  and CloudTrail decrypt visibility. An AWS-managed key rotates on AWS's
  schedule with no customer visibility. Missing a customer-managed key is
  CONFIG_GAP, not OK — but it is NOT NO_ENCRYPTION because data is still
  encrypted.

- **MSK Serverless has fundamentally different security defaults.**
  Serverless clusters enforce TLS in-transit, use IAM auth exclusively,
  do not support UNAUTHENTICATED, and cannot be made public. A Serverless
  cluster can only fail the logging dimension (Step 4). Do NOT apply
  Steps 1-3 to a Serverless cluster — it produces false positives. Check
  `ClusterType` first.

- **Public access requires the cluster to be in public subnets.**
  `PublicAccess.Type: SERVICE_PROVIDED_EIPS` attaches Elastic IPs to
  brokers. This only works if the broker subnets route to an Internet
  Gateway. A cluster in private subnets with public access enabled is a
  configuration error — MSK will accept the setting but the brokers
  remain unreachable from the internet. Still flag as PUBLIC_ACCESS
  because the intent (public exposure) is present even if the network
  topology doesn't complete the path.

- **`PublicAccess.Type: DISABLED` is NOT the absence of public access.**
  It is the explicit "off" state. An absent `ConnectivityInfo` block also
  means no public access. Both are safe — do not flag either as
  PUBLIC_ACCESS.

- **MSK encryption settings are immutable after creation.** Unlike
  EKS (which can toggle endpoint access with update-cluster-config), MSK
  cannot change `ClientBroker`, `InClusterEncryption`, or authentication
  modes after the cluster is created. Remediation for NO_ENCRYPTION or
  UNAUTHENTICATED requires creating a NEW cluster with the correct
  settings and migrating topics. State this explicitly in the
  remediation — operators often expect an in-place fix that does not
  exist.

- **SASL/SCRAM secrets live in AWS Secrets Manager with a mandated tag.**
  MSK discovers SCRAM credentials via secrets tagged
  `AmazonMSK_20181101`. A secret without this tag is invisible to MSK —
  clients configured for SCRAM fail with `SASL_AUTHENTICATION_FAILED`.
  When auditing SCRAM auth, verify the secret exists and has the tag, not
  just that `Sasl.Scram.enabled: true`.

- **mTLS requires an ACM Private Certificate Authority (PCA).** The
  `ClientAuthentication.Tls.CertificateAuthorityArnList` must reference a
  PCA ARN. A self-managed CA (uploaded as a truststore) is NOT supported
  on MSK Provisioned — only ACM PCA. The PCA costs ~$400/month; operators
  sometimes skip it and fall back to SASL only, which is valid but loses
  the mutual-identity guarantee of mTLS.

- **Broker logging destinations are independently toggleable.** MSK
  supports four log destinations: CloudWatch Logs, S3, Kinesis Data
  Firehose, and broker logs delivered to a specified destination. Each
  has its own `Enabled` flag. A cluster with only `S3.Enabled: true` and
  `CloudWatchLogs.Enabled: false` is logging — do NOT flag it as a
  logging gap. The requirement is at least ONE destination enabled.

- **Enhanced monitoring is separate from broker logging.**
  `EnhancedMonitoring: DEFAULT` controls the granularity of MSK metrics
  (broker-level vs per-topic-per-broker). It is a monitoring-level
  setting, not a security-forensic logging destination. Do NOT flag
  `EnhancedMonitoring: DEFAULT` as a logging gap — it is an operational
  advisory, not a CONFIG_GAP driver.

- **Open Monitoring (Prometheus) is a third-party integration layer.**
  `OpenMonitoring.Prometheus.JmxExporter.Enabled` or
  `NodeExporter.Enabled` controls Prometheus scrape endpoints. Missing
  Open Monitoring is NOT a logging gap — it is an observability choice.
  Do not confuse it with broker log delivery.

- **MSK configuration properties (auto.create.topics, unclean.leader.election)
  live in a separate describe-configuration call.** The `describe-cluster`
  output does NOT include Kafka broker properties. If the input includes
  configuration properties, audit them; if not, note that broker-level
  Kafka configuration was not provided and cannot be assessed (advisory,
  not a verdict driver).

- **`auto.create.topics.enable=true` is a silent privilege-escalation
  vector.** Any Kafka client can create topics with default replication
  and retention — including topics that capture sensitive data streams
  with no lifecycle policy. If the MSK configuration includes
  `auto.create.topics.enable=true`, flag it as a CONFIG_GAP finding
  regardless of the verdict.

- **`unclean.leader.election.enable=true` can cause data loss.** When a
  partition leader fails and no in-sync replica is available, an out-of-
  sync replica becomes leader, losing acknowledged messages. Flag as a
  CONFIG_GAP finding if present in the MSK configuration.

- **MSK does not support Security Groups on the cluster itself.** Broker
  security groups are attached to the broker ENIs (Elastic Network
  Interfaces), not to a cluster-level construct. They are found in
  `BrokerNodeGroupInfo.SecurityGroups` or queried via
  `aws ec2 describe-network-interfaces --filter Name=description,Values=MSK*`.
  A broker SG with `0.0.0.0/0` on port 9094 (TLS) or 9092 (plaintext)
  is an exposure — flag it as an additional CONFIG_GAP finding.

## Recent AWS features (2024-2026)

- **MSK Serverless GA (2024):** MSK Serverless auto-scales capacity without managing brokers. Auditors should note that MSK Serverless changes the audit surface — there are no broker instances to audit (no broker public access, no per-broker logging). Instead, verify the serverless cluster's VPC configuration, IAM/TLS authentication, and Kafka version compatibility.
- **MSK Connect updates (2024-2025):** Enhanced MSK Connect with more connector types and improved error handling. Auditors should verify that MSK Connect worker configurations use encrypted connections and that connector logs are enabled.
- **KRaft mode (2024-2025):** MSK now supports KRaft (Kafka Raft) mode, eliminating the ZooKeeper dependency. Auditors should verify that KRaft-mode clusters have appropriate monitoring — ZooKeeper-specific metrics no longer apply.
- **IAM authentication enhancements (2024):** Expanded IAM auth support for Kafka client connections. Auditors should verify that clusters enforce IAM or TLS client authentication and that `unauthenticated` access is disabled.

