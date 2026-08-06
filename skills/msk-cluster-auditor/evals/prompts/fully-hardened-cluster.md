# Eval prompt: fully-hardened-cluster

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: fully-hardened-cluster
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/fully-hardened-cluster
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-fully-hardened

ClientAuthentication:
  Tls:
    Enabled: true
    CertificateAuthorityArnList:
      - arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/def-456
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
      LogGroup: /aws/kafka/fully-hardened-cluster
    S3:
      Enabled: true
      Bucket: msk-logs-fully-hardened-cluster
