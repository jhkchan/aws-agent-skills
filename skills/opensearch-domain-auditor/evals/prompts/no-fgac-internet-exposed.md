# Eval prompt: no-fgac-internet-exposed

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: no-fgac-internet-exposed
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/no-fgac-internet-exposed
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
    Enabled: true
    KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/customer-cmk-12345
  NodeToNodeEncryptionOptions:
    Enabled: true
  DomainEndpointOptions:
    EnforceHTTPS: true
  AdvancedSecurityOptions:
    Enabled: false
  LogPublishingOptions:
    SEARCH_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/no-fgac-internet-exposed/search-slow
    INDEX_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/no-fgac-internet-exposed/index-slow
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
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/no-fgac-internet-exposed/*"
    },
    {
      "Sid": "AppHttp",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-search-role"},
      "Action": "es:ESHttp*",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/no-fgac-internet-exposed/*"
    }
  ]
}
```
