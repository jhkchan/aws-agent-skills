# End-to-end usage scenario: msk-cluster-auditor

A walkthrough showing the skill auditing an MSK cluster that has both
ClientBroker TLS_PLAINTEXT (NO_ENCRYPTION — plaintext path active) and
all broker logging disabled (CONFIG_GAP), demonstrating the first-match
priority logic, the TLS_PLAINTEXT-vs-TLS distinction, and the
immutability-aware remediation workflow.

## Input (user prompt)

> Review this MSK cluster before we start sending production event data
> through it. It was created by a previous team member and I want to make
> sure the security posture is adequate.

```yaml
Cluster name: event-bus-prod
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/event-bus-prod
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS_PLAINTEXT
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-event-bus

ClientAuthentication:
  Tls:
    Enabled: true
    CertificateAuthorityArnList:
      - arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/prod-ca
  Sasl:
    Iam:
      Enabled: true
  Unauthenticated:
    Enabled: false

BrokerNodeGroupInfo:
  ConnectivityInfo:
    PublicAccess:
      Type: DISABLED

LoggingInfo:
  BrokerLogs:
    CloudWatchLogs:
      Enabled: false
    S3:
      Enabled: false
    Firehose:
      Enabled: false
```

## Skill output

```text
CLUSTER: event-bus-prod
VERDICT: NO_ENCRYPTION
REASON: ClientBroker is TLS_PLAINTEXT — a dual-mode listener that publishes
both TLS and plaintext ports. Clients connecting over the plaintext port send
all data unencrypted, breaking the encryption guarantee (Step 1). Broker
logging is also fully disabled (Step 4a).
FINDINGS:
  - [NO_ENCRYPTION] ClientBroker: TLS_PLAINTEXT — plaintext listener is
    active, clients can bypass TLS entirely (Step 1)
  - [CONFIG_GAP] InClusterEncryption is true (good), but all broker log
    destinations (CloudWatch, S3, Firehose) are disabled — no forensic
    record (Step 4a)
  - [OK] ClientAuthentication: mTLS + SASL/IAM enabled, unauthenticated
    disabled (Step 2)
  - [OK] PublicAccess: DISABLED — brokers are private (Step 3)
  - [OK] EncryptionAtRest: customer-managed KMS key configured (Step 4b)
REMEDIATION:
  1. MSK encryption settings are immutable post-creation. Create a new
     cluster with ClientBroker: TLS (not TLS_PLAINTEXT) and migrate topics
     using MirrorMaker 2 or MSK Replicator. This is NOT an in-place fix.
  2. On the replacement cluster, enable broker logging to CloudWatch:
     set LoggingInfo.BrokerLogs.CloudWatchLogs.Enabled: true.
  3. Set a retention policy on the log group:
     aws logs put-retention-policy --log-group-name /aws/kafka/<new-cluster>
     --retention-in-days 90
```

## Why the verdict is NO_ENCRYPTION, not CONFIG_GAP

The operator's initial reaction might be "TLS is available, so it's just
a config gap." The skill's classification logic corrects this:

- `TLS_PLAINTEXT` publishes **two** listeners: a TLS port (9094) and a
  plaintext port (9092). A client that connects to port 9092 sends
  credentials, message payloads, and topic metadata in cleartext.
- The existence of a TLS path does not compensate for the plaintext path —
  any client can choose either, and there is no protocol-level enforcement
  that forces TLS.
- Therefore the verdict is NO_ENCRYPTION (Step 1, first match), which is
  higher priority than the logging gap (Step 4a, CONFIG_GAP).

The finding is listed as CONFIG_GAP in the FINDINGS list, but the verdict
is NO_ENCRYPTION because first-match-wins by priority order.

## Remediation workflow — migration, not in-place fix

Unlike services where encryption can be toggled (e.g., EKS endpoint
access, S3 bucket policies), MSK's `ClientBroker` setting is **immutable**
after cluster creation. The remediation path is:

1. Create a new MSK cluster with `ClientBroker: TLS` (not TLS_PLAINTEXT)
   and `InClusterEncryption: true`.
2. Mirror topics from the old cluster using MirrorMaker 2 or Amazon MSK
   Replicator.
3. Validate consumer group offsets on the new cluster.
4. Cut over producers and consumers.
5. Verify broker logging is delivering to CloudWatch on the new cluster.
6. Decommission the old cluster.

This is a multi-day operation, not a one-line CLI fix. The skill surfaces
this constraint explicitly so operators do not waste time searching for an
in-place update command that does not exist.
