# Eval prompt: config-gap-no-ntn-weak-master-no-slowlogs

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: config-gap-no-ntn-weak-master-no-slowlogs
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/config-gap-no-ntn-weak-master-no-slowlogs
Domain configuration (describe-domain-config):
  EngineVersion: OpenSearch_2.11
  ClusterConfig:
    DedicatedMasterEnabled: true
    DedicatedMasterType: t3.small.search
    DedicatedMasterCount: 3
    InstanceType: m5.large.search
    InstanceCount: 3
    ZoneAwarenessEnabled: false
  EncryptionAtRestOptions:
    Enabled: true
    KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/customer-cmk-12345
  NodeToNodeEncryptionOptions:
    Enabled: false
  DomainEndpointOptions:
    EnforceHTTPS: false
  AdvancedSecurityOptions:
    Enabled: true
    InternalUserDatabaseEnabled: false
  LogPublishingOptions: {}
Access policy (describe-domain-access-policy):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "es:*",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/config-gap-no-ntn-weak-master-no-slowlogs/*"
    }
  ]
}
```
