# Eval prompt: overpermissive-ec2-role

Audit the following EMR cluster configuration for security exposure. Emit the
standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: j-OVERPERMEC2R01
Cluster name: overpermissive-ec2-role
Cluster metadata (describe-cluster):
  ReleaseLabel: emr-6.10.0
  AutoTerminate: false
  SecurityConfiguration: full-encryption-config
  ServiceRole: EMR_DefaultRole
  Ec2InstanceAttributes.IamInstanceProfile: EMR_EC2_CustomRole
  AutoScalingRole: EMR_AutoScaling_DefaultRole
  LogUri: s3://emr-logs/overpermissive-ec2-role/
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
    InTransitEncryptionConfiguration:
      TLSCertificateConfiguration:
        CertificateProviderType: PEM
        S3Object: s3://emr-certs/overpermissive-ec2-role/certchain.pem

IAM role summaries:
  ServiceRole (EMR_DefaultRole): AmazonElasticMapReduceRole (AWS managed)
  EC2 instance profile (EMR_EC2_CustomRole):
    Managed policies: AmazonElasticMapReduceforEC2Role
    Inline policy "S3FullAccess":
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Action: "s3:*"
          Resource: "*"
  AutoScalingRole (EMR_AutoScaling_DefaultRole): AmazonElasticMapReduceAutoScalingRole (AWS managed)
