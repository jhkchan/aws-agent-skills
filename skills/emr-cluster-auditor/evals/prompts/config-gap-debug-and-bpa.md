# Eval prompt: config-gap-debug-and-bpa

Audit the following EMR cluster configuration for security exposure. Emit the
standard VERDICT block (CLUSTER, VERDICT, REASON, FINDINGS, REMEDIATION).

Cluster id: j-CONFIGGAPDBG01
Cluster name: config-gap-debug-and-bpa
Cluster metadata (describe-cluster):
  ReleaseLabel: emr-6.10.0
  AutoTerminate: false
  SecurityConfiguration: full-encryption-config
  ServiceRole: EMR_DefaultRole
  Ec2InstanceAttributes.IamInstanceProfile: EMR_EC2_ScopedRole
  AutoScalingRole: EMR_AutoScaling_DefaultRole
  LogUri: (none — debug logging disabled)
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
        S3Object: s3://emr-certs/config-gap-debug-and-bpa/certchain.pem

Block Public Access configuration (get-block-public-access-configuration):
  BlockPublicSecurityGroupRules: false

IAM role summaries:
  ServiceRole (EMR_DefaultRole): AmazonElasticMapReduceRole (AWS managed)
  EC2 instance profile (EMR_EC2_ScopedRole):
    Inline policy "ScopedS3":
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Action: ["s3:GetObject", "s3:ListBucket"]
          Resource: ["arn:aws:s3:::emr-input", "arn:aws:s3:::emr-input/*"]
  AutoScalingRole (EMR_AutoScaling_DefaultRole): AmazonElasticMapReduceAutoScalingRole (AWS managed)
