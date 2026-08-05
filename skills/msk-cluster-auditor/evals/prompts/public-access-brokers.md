# Eval prompt: public-access-brokers

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: public-access-brokers
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/public-access-brokers
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-public-access

ClientAuthentication:
  Sasl:
    Iam:
      Enabled: true
  Unauthenticated:
    Enabled: false

BrokerNodeGroupInfo:
  ConnectivityInfo:
    PublicAccess:
      Type: SERVICE_PROVIDED_EIPS

LoggingInfo:
  BrokerLogs:
    S3:
      Enabled: true
      Bucket: msk-logs-public-access-brokers
    CloudWatchLogs:
      Enabled: true
      LogGroup: /aws/kafka/public-access-brokers
