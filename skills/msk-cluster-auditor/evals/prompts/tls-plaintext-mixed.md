# Eval prompt: tls-plaintext-mixed

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: tls-plaintext-mixed
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/tls-plaintext-mixed
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS_PLAINTEXT
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-tls-plaintext

ClientAuthentication:
  Tls:
    Enabled: true
    CertificateAuthorityArnList:
      - arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/abc-123
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
    S3:
      Enabled: true
      Bucket: msk-logs-tls-plaintext-mixed
