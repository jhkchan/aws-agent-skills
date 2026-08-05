---
description: Audit an Amazon MSK (Managed Streaming for Kafka) cluster for encryption in-transit (TLS), encryption at-rest (KMS CMK), client authentication (TLS/IAM/SCRAM/unauthenticated), broker logging (CloudWatch/S3/Firehose), and public access exposure.
nl_triggers:
  - "audit this MSK cluster"
  - "check MSK encryption"
  - "is my Kafka cluster encrypted"
  - "MSK unauthenticated access"
  - "is my MSK cluster public"
  - "check MSK broker logging"
  - "Kafka plaintext broker"
  - "MSK authentication modes"
  - "TLS_PLAINTEXT Kafka"
  - "MSK cluster security"
  - "hardening MSK cluster"
  - "MSK SASL SCRAM audit"
  - "MSK mTLS check"
routes_to: msk-cluster-auditor
---

# /aws:audit-msk-cluster

Activate the `msk-cluster-auditor` skill and audit one or more Amazon MSK
cluster configurations for security exposure.

## What it does

Reads an MSK cluster configuration (describe-cluster output or equivalent
JSON) and applies the ordered classification logic:

1. Pre-flight cluster metadata gate — short-circuit MSK Serverless clusters
   (forced TLS + IAM auth, no public access).
2. Encryption in-transit — ClientBroker PLAINTEXT or TLS_PLAINTEXT is
   NO_ENCRYPTION (plaintext path breaks the encryption guarantee).
3. Client authentication — Unauthenticated.Enabled: true is UNAUTHENTICATED
   (open data plane).
4. Public access — PublicAccess.Type: SERVICE_PROVIDED_EIPS is PUBLIC_ACCESS
   (brokers internet-reachable via Elastic IPs).
5. Logging + at-rest — All broker log destinations disabled or no
   customer-managed KMS key is CONFIG_GAP.
6. Aggregation — first match wins (NO_ENCRYPTION > UNAUTHENTICATED >
   PUBLIC_ACCESS > CONFIG_GAP > OK).

Emits a deterministic VERDICT per cluster:

```text
CLUSTER: <cluster-name>
VERDICT: NO_ENCRYPTION | UNAUTHENTICATED | PUBLIC_ACCESS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step 1)>
  - [CONFIG_GAP] <finding description (Step 4a/4b)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an MSK cluster configuration and ask any of:

- "audit this MSK cluster"
- "is my Kafka traffic encrypted?"
- "are unauthenticated clients allowed?"
- "is my MSK cluster exposed to the internet?"
- "check broker logging coverage"

A cluster ARN or name + any audit verb ("audit this cluster", "check MSK
security") also routes here via the orchestrator.

## Inputs

- An MSK cluster configuration (JSON from describe-cluster), pasted inline
  or referenced by file path.
- Key fields: ClusterType, EncryptionInfo (ClientBroker, InClusterEncryption,
  DataVolumeKMSKeyId), ClientAuthentication (Tls, Sasl.Iam, Sasl.Scram,
  Unauthenticated), BrokerNodeGroupInfo.ConnectivityInfo.PublicAccess,
  LoggingInfo.BrokerLogs.
- Optionally: MSK configuration properties (from describe-configuration) for
  auto.create.topics and unclean.leader.election checks.

## Outputs

- One VERDICT block per cluster (multiple findings listed, first-match
  verdict wins by priority).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: noting MSK encryption immutability where relevant
  (create new cluster + migrate), disable public access, enable logging,
  disable unauthenticated access.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for MSK/Kafka Analytics security).
- `/aws:audit-kms-key-policy` for auditing the customer-managed KMS key
  used by the MSK cluster for encryption at rest.
