# Eval prompt: no-encryption-and-public-worst-first

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: no-encryption-and-public-worst-first
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/no-encryption-and-public-worst-first
Domain configuration (describe-domain-config):
  EngineVersion: OpenSearch_2.11
  ClusterConfig:
    DedicatedMasterEnabled: true
    DedicatedMasterType: m5.large.search
    DedicatedMasterCount: 3
    InstanceType: m5.large.search
    InstanceCount: 3
    ZoneAwarenessEnabled: true
  EncryptionAtRestOptions:
    Enabled: false
  NodeToNodeEncryptionOptions:
    Enabled: false
  DomainEndpointOptions:
    EnforceHTTPS: false
  AdvancedSecurityOptions:
    Enabled: false
  LogPublishingOptions: {}
Access policy (describe-domain-access-policy):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "es:ESHttp*",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/no-encryption-and-public-worst-first/*"
    }
  ]
}
```
