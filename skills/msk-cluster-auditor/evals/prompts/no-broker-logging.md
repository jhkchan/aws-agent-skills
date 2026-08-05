# Eval prompt: no-broker-logging

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: no-broker-logging
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/no-broker-logging
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-no-logging

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
      Enabled: false
    S3:
      Enabled: false
    Firehose:
      Enabled: false
