# Eval prompt: disabled-policy

Policy id: policy-disabled-policy
DLM lifecycle policy (from get-lifecycle-policy):
  Description: production-ebs-daily
  State: DISABLED
  PolicyType: EBS_SNAPSHOT_POLICY
  DateCreated: 2025-06-01T10:00:00Z
  PolicyDetails:
    ResourceTypes: ["VOLUME"]
    TargetTags: [{"Key": "Environment", "Values": ["production"]}]
    Schedules:
      - Name: daily-6am
        CreateRule:
          Interval: 24
          IntervalUnit: HOURS
          Times: ["06:00"]
        RetainRule:
          Count: 14
        CopyTags: true
        CrossRegionCopyTargets: []

Audit this DLM lifecycle policy. Emit the standard VERDICT block (POLICY,
VERDICT, REASON, FINDINGS, REMEDIATION).
