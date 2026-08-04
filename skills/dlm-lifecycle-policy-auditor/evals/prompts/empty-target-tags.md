# Eval prompt: empty-target-tags

Policy id: policy-empty-target-tags
DLM lifecycle policy (from get-lifecycle-policy):
  Description: stale-dev-backup
  State: ENABLED
  PolicyType: EBS_SNAPSHOT_POLICY
  DateCreated: 2025-03-15T08:00:00Z
  PolicyDetails:
    ResourceTypes: ["VOLUME"]
    TargetTags: []
    Schedules:
      - Name: daily-2am
        CreateRule:
          Interval: 24
          IntervalUnit: HOURS
          Times: ["02:00"]
        RetainRule:
          Count: 7
        CopyTags: true

Audit this DLM lifecycle policy. Emit the standard VERDICT block (POLICY,
VERDICT, REASON, FINDINGS, REMEDIATION).
