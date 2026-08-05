# Eval prompt: public-access-wildcard-http

Audit the following Amazon OpenSearch Service domain configuration for
security exposure and compliance posture. Emit the standard VERDICT block
(DOMAIN, VERDICT, REASON, FINDINGS, REMEDIATION).

Domain name: public-access-wildcard-http
Domain ARN: arn:aws:es:us-east-1:111111111111:domain/public-access-wildcard-http
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
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/public-access-wildcard-http/search-slow
    INDEX_SLOW_LOGS:
      Enabled: true
      CloudWatchLogsLogGroupArn: arn:aws:logs:us-east-1:111111111111:log-group:/aws/opensearch/public-access-wildcard-http/index-slow
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
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/public-access-wildcard-http/*"
    }
  ]
}
```
