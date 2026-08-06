# Eval prompt: plaintext-broker

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: plaintext-broker
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/plaintext-broker
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: PLAINTEXT
    InClusterEncryption: false
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-plaintext-broker

ClientAuthentication:
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
      Enabled: true
      LogGroup: /aws/kafka/plaintext-broker
