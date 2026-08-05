# End-to-end usage scenario: emr-cluster-auditor

A walkthrough showing the skill auditing an EMR cluster that has full
encryption but an over-permissive EC2 instance profile role
(OVERPERMISSIVE_ROLE), demonstrating the ordered classification logic, the
SecurityConfiguration-as-separate-API concept, and the cluster-recreation
remediation workflow.

## Input (user prompt)

> Audit this EMR cluster before we use it for the production Spark data
> pipeline. It processes PII from the S3 data lake.

```text
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
```

## Skill output

```text
CLUSTER: j-OVERPERMEC2R01 (overpermissive-ec2-role)
VERDICT: OVERPERMISSIVE_ROLE
REASON: EC2 instance profile role "EMR_EC2_CustomRole" grants s3:* on Resource
"*" (Step 2b) — the data-processing identity has unrestricted S3 read/write/delete
access across every bucket in the account, including the PII data lake.
FINDINGS:
  - [OVERPERMISSIVE_ROLE] EC2 instance profile inline policy "S3FullAccess"
    grants s3:* on Resource "*" (Step 2b) — unrestricted S3 access to all
    buckets, including buckets unrelated to this workload
  - [OK] All three encryption layers present: S3 SSE-KMS, local-disk LUKS
    via KMS, in-transit TLS via PEM certificate (Step 1 — passed)
  - [OK] Service role and AutoScaling role use AWS managed defaults — no
    custom wildcard policies detected (Step 2)
  - [CONFIG_GAP] Kerberos authentication not enabled (Step 3c) — cluster
    relies solely on IAM for access control
REMEDIATION:
  1. Replace the EC2 instance profile inline policy "S3FullAccess" with
     scoped permissions on the specific data-lake buckets:
     aws iam put-role-policy --role-name EMR_EC2_CustomRole \
       --policy-name ScopedS3Access \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::pii-datalake","arn:aws:s3:::pii-datalake/*"]},{"Effect":"Allow","Action":["s3:PutObject"],"Resource":["arn:aws:s3:::emr-output/*"]}]}'
  2. For PII workloads, enable Kerberos authentication (requires cluster
     recreation with KerberosAttributes).
  3. Note: IAM role changes take effect within seconds but running instances
     may cache credentials for up to 1 hour (EC2 metadata refresh interval).
```

## What the skill caught that a generic assistant misses

1. **The SecurityConfiguration is a separate API call.** A generic assistant
   sees `SecurityConfiguration: full-encryption-config` on the cluster
   metadata and might assume encryption is configured. The skill recognises
   that the cluster metadata only returns the config NAME — the actual
   encryption settings must be fetched via `describe-security-configuration`.
   The skill evaluates all three encryption layers explicitly from the parsed
   config contents.

2. **The EC2 instance profile is the data-processing identity.** A generic
   assistant might flag `s3:*` as "broad" without explaining WHY it is
   dangerous in the EMR context. The skill identifies this role as the
   identity that processes every S3 object the cluster touches — `s3:*` on
   `*` means the role can read, delete, or overwrite any bucket in the
   account, including unrelated production data.

3. **Ordered classification with aggregation.** The encryption layers pass
   (all three present), but the role audit fails (Step 2b). The verdict is
   OVERPERMISSIVE_ROLE — not OK despite correct encryption. The FINDINGS list
   shows both the failing dimension and the passing ones, so the operator
   knows exactly what to fix and what is already working.

4. **The credential-refresh delay.** The skill warns that tightening the EC2
   role does not instantly affect running instances — the EC2 metadata
   service caches instance-profile credentials for up to 1 hour. This prevents
   the operator from assuming the fix is immediately effective.

## Slash-command invocation

```
/aws:audit-emr-cluster
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this EMR cluster before we use it for the production pipeline"
```

The orchestrator emits
`[Phase: Audit | Skills routed: emr-cluster-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this EMR cluster"
# [Phase: Audit | Skills routed: emr-cluster-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the role, validate the cluster posture:

```bash
# Verify the inline policy was replaced
aws iam get-role-policy --role-name EMR_EC2_CustomRole \
  --policy-name ScopedS3Access --profile default

# Verify the SecurityConfiguration encryption settings
aws emr describe-security-configuration \
  --name full-encryption-config --profile default | jq .

# Check Block Public Access for the region
aws emr get-block-public-access-configuration --profile default
```

Then monitor CloudTrail for `s3:GetObject` / `s3:DeleteObject` events from
the EMR EC2 role ARN for 1 hour (the credential-refresh window).
