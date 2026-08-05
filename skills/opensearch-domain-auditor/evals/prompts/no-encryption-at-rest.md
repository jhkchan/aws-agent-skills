# Eval prompt: no-encryption-at-rest

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: no-encryption-at-rest
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/no-encryption-at-rest
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
    Enabled: true
  DomainEndpointOptions:
    EnforceHTTPS: true
  AdvancedSecurityOptions:
    Enabled: true
    InternalUserDatabaseEnabled: false
  LogPublishingOptions:
    SEARCH_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/no-encryption-at-rest/search-slow
    INDEX_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/no-encryption-at-rest/index-slow
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
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/no-encryption-at-rest/*"
    },
    {
      "Sid": "AppRead",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-reader"},
      "Action": ["es:ESHttpGet", "es:ESHttpHead"],
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/no-encryption-at-rest/*"
    }
  ]
}
```
