# Eval prompt: unauthenticated-clients

Audit the following Amazon MSK cluster configuration for security exposure.
Emit the standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster name: unauthenticated-clients
Cluster ARN: arn:aws:kafka:us-east-1:111111111111:cluster/unauthenticated-clients
Cluster type: PROVISIONED
State: ACTIVE

EncryptionInfo:
  EncryptionInTransit:
    ClientBroker: TLS
    InClusterEncryption: true
  EncryptionAtRest:
    DataVolumeKMSKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-unauth-clients

ClientAuthentication:
  Sasl:
    Iam:
      Enabled: true
  Unauthenticated:
    Enabled: true

BrokerNodeGroupInfo:
  ConnectivityInfo:
    PublicAccess:
      Type: DISABLED

LoggingInfo:
  BrokerLogs:
    CloudWatchLogs:
      Enabled: true
      LogGroup: /aws/kafka/unauthenticated-clients
