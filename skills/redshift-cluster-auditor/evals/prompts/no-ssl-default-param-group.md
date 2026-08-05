# Eval prompt: no-ssl-default-param-group

Audit the following Amazon Redshift cluster configuration for security
exposure and configuration gaps. Emit the standard VERDICT block (CLUSTER,
VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster identifier: no-ssl-default-param-group
Cluster ARN: arn:aws:redshift:us-east-1:111111111111:cluster:no-ssl-default-param-group

Cluster metadata (describe-clusters):
- ClusterStatus: available
- NumberOfNodes: 4
- NodeType: ra3.4xlarge
- PubliclyAccessible: false
- Encrypted: true
- KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/abc-123
- EnhancedVPCRouting: true
- ClusterParameterGroupName: default.redshift-1.0
- ClusterParameterGroupStatus: in-sync
- AutomatedSnapshotRetentionPeriod: 7
- VpcSecurityGroups: [{VpcSecurityGroupId: sg-0ccc55556666, Status: active}]

Parameter group parameters (default.redshift-1.0):
- require_ssl = false (Source: engine-default)
- enable_user_activity_logging = true (Source: user)

Logging status (describe-logging-status):
- LoggingEnabled: true
- BucketName: audit-logs-111111111111
- S3KeyPrefix: redshift/no-ssl-default-param-group/

Security group sg-0ccc55556666 ingress rules (describe-security-groups):
- tcp 5439-5439 from 10.0.0.0/16
