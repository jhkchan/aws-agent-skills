# Eval prompt: ok-clean-production

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: ok-clean-production
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/ok-clean-production
Domain configuration (describe-domain-config):
  EngineVersion: OpenSearch_2.11
  ClusterConfig:
    DedicatedMasterEnabled: true
    DedicatedMasterType: m5.large.search
    DedicatedMasterCount: 3
    InstanceType: m5.large.search
    InstanceCount: 3
    ZoneAwarenessEnabled: true
    ZoneAwarenessConfig:
      AvailabilityZoneCount: 3
  EncryptionAtRestOptions:
    Enabled: true
    KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/prod-cmk-67890
  NodeToNodeEncryptionOptions:
    Enabled: true
  DomainEndpointOptions:
    EnforceHTTPS: true
  AdvancedSecurityOptions:
    Enabled: true
    InternalUserDatabaseEnabled: false
  VPCOptions:
    SubnetIds: ["subnet-abc", "subnet-def", "subnet-ghi"]
    SecurityGroupIds: ["sg-private"]
  LogPublishingOptions:
    SEARCH_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/ok-clean-production/search-slow
    INDEX_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/ok-clean-production/index-slow
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
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/ok-clean-production/*"
    },
    {
      "Sid": "AppHttp",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-search-role"},
      "Action": ["es:ESHttpGet", "es:ESHttpHead", "es:ESHttpPost"],
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/ok-clean-production/*"
    }
  ]
}
```
