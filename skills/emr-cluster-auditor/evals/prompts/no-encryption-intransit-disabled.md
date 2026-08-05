# Eval prompt: no-encryption-intransit-disabled

Audit the following EMR cluster configuration for security exposure. Emit the
standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: j-NOENCINTRANS01
Cluster name: no-encryption-intransit-disabled
Cluster metadata (describe-cluster):
  ReleaseLabel: emr-6.10.0
  AutoTerminate: false
  SecurityConfiguration: partial-encryption-config
  ServiceRole: EMR_DefaultRole
  Ec2InstanceAttributes.IamInstanceProfile: EMR_EC2_DefaultRole
  AutoScalingRole: EMR_AutoScaling_DefaultRole
  LogUri: s3://emr-logs/no-encryption-intransit-disabled/
  KerberosAttributes: (none)
  VisibleToAllUsers: false
  InstanceGroups:
    - InstanceGroupType: MASTER, InstanceType: m5.xlarge, RequestedInstanceCount: 1
    - InstanceGroupType: CORE, InstanceType: m5.xlarge, RequestedInstanceCount: 3

SecurityConfiguration contents (describe-security-configuration):
  EncryptionConfiguration:
    AtRestEncryptionConfiguration:
      S3EncryptionConfiguration:
        EncryptionMode: SSE-KMS
        AwsKmsKey: arn:aws:kms:us-east-1:111111111111:key/abc-123
      LocalDiskEncryptionConfiguration:
        EncryptionKeyProviderType: AwsKms
        AwsKmsKey: arn:aws:kms:us-east-1:111111111111:key/def-456
    InTransitEncryptionConfiguration: (absent)

IAM role summaries:
  ServiceRole (EMR_DefaultRole): AmazonElasticMapReduceRole (AWS managed)
  EC2 instance profile (EMR_EC2_DefaultRole): AmazonElasticMapReduceforEC2Role (AWS managed)
  AutoScalingRole (EMR_AutoScaling_DefaultRole): AmazonElasticMapReduceAutoScalingRole (AWS managed)
