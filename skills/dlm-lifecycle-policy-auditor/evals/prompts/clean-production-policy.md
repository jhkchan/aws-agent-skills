# Eval prompt: clean-production-policy

Policy id: policy-clean-production-policy
DLM lifecycle policy (from get-lifecycle-policy):
  Description: production-ebs-full-backup
  State: ENABLED
  PolicyType: EBS_SNAPSHOT_POLICY
  DateCreated: 2024-11-05T14:00:00Z
  PolicyDetails:
    ResourceTypes: ["VOLUME"]
    TargetTags: [{"Key": "Environment", "Values": ["production"]}]
    Schedules:
      - Name: daily-6am-with-dr
        CreateRule:
          CronExpression: "0 6 * * ? *"
          Times: ["06:00"]
        RetainRule:
          Count: 30
        CopyTags: true
        CrossRegionCopyTargets:
          - TargetRegion: us-west-2
            EncryptionConfiguration:
              Encrypted: true
              CmkArn: arn:aws:kms:us-west-2:111111111111:key/dr-cmk-abc123

Audit this DLM lifecycle policy. Emit the standard VERDICT block (POLICY,
VERDICT, REASON, FINDINGS, REMEDIATION).
