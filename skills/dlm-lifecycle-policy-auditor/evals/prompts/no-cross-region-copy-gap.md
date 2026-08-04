# Eval prompt: no-cross-region-copy-gap

Policy id: policy-no-cross-region-copy-gap
DLM lifecycle policy (from get-lifecycle-policy):
  Description: prod-volumes-daily
  State: ENABLED
  PolicyType: EBS_SNAPSHOT_POLICY
  DateCreated: 2025-01-20T12:00:00Z
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
