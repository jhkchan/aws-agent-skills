# Eval prompt: short-retention-no-copy-tags-gap

Policy id: policy-short-retention-no-copy-tags-gap
DLM lifecycle policy (from get-lifecycle-policy):
  Description: minimal-backup
  State: ENABLED
  PolicyType: EBS_SNAPSHOT_POLICY
  DateCreated: 2025-04-10T09:00:00Z
  PolicyDetails:
    ResourceTypes: ["VOLUME"]
    TargetTags: [{"Key": "App", "Values": ["billing"]}]
    Schedules:
      - Name: daily-3am
        CreateRule:
          Interval: 24
          IntervalUnit: HOURS
          Times: ["03:00"]
        RetainRule:
          Count: 1
        CopyTags: false
        CrossRegionCopyTargets: []

Audit this DLM lifecycle policy. Emit the standard VERDICT block (POLICY,
VERDICT, REASON, FINDINGS, REMEDIATION).
