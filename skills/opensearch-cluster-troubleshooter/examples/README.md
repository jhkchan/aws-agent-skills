# Example usage: opensearch-cluster-troubleshooter

A walkthrough showing the skill diagnosing a `ClusterBlockException`
that initially looks like a generic "OpenSearch is broken" outage,
demonstrating the symptom-to-layer triage, the disk-watermark
three-stage clutch model (85% / 90% / 95%), the evidence-backed
ROOT_CAUSE_IDENTIFIED verdict, and the unbounded-growth upstream
cause.

## Input (user prompt)

> Our logs cluster started failing writes at 03:17 UTC. Every write
> returns `ClusterBlockException: blocked by: [FORBIDDEN/12/index
> read-only / delete admin api]`. Reads still work. We've been
> debugging this as "OpenSearch is broken" for 30 minutes — please
> help us find the actual root cause.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
HotDataNodes: 3 (r6g.large.search, EBS 100 GB each)
MasterNodes: 3
ClusterStatus: yellow

_cat/allocation?v output:
  data-1  disk.percent=91  disk.used=91.2gb  disk.avail=8.8gb
  data-2  disk.percent=88  disk.used=89.8gb  disk.avail=10.2gb
  data-3  disk.percent=97  disk.used=97.0gb  disk.avail=3.0gb

CloudWatch metrics (last 30 min):
  - ClusterIndexWritesBlocked: 1 (sustained 12 min)
  - FreeStorageSpace Minimum: 3.0 GB on data-3
  - JVMHeapPressure Average: 41% (heap is NOT the issue)
  - ClusterStatus.yellow: 1

_cat/indices/logs-*?v&s=index (summary):
  427 monthly indices from 2023-02 to 2024-12
  Oldest 14 months have not been queried in 30 days
  No ISM policy attached to any logs-* index
```

## Skill output

```text
TARGET: prod-logs-cluster
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: ClusterBlockException is the flood-stage read-only
  block; node `prod-logs-cluster-data-3` is at 97% disk (above
  the 95% flood watermark); unbounded index growth — `logs-*`
  indices dating back 14 months have no ISM policy to roll over
  or delete. The disk pressure that triggered the block is the
  upstream cause; the block itself is the symptom.
LAYER: DISK_WATERMARK_FLOOD
EVIDENCE:
  - Symptom: every write returns `ClusterBlockException: blocked
    by: [FORBIDDEN/12/index read-only / delete admin api]`;
    `ClusterIndexWritesBlocked` CloudWatch metric = 1 for 12 min.
  - Probe: `_cat/allocation?v` shows data-3 at `disk.percent: 97`
    (above the 95% flood_stage watermark). The other two nodes
    are at 91% (above the 90% high watermark — already evacuating)
    and 88% (above the 85% low watermark — not receiving new
    shards).
  - Probe: `_cat/indices/logs-*?v&s=index` returns 427 monthly
    indices from 2023-02 to 2024-12; the oldest 14 months have
    not been queried in 30 days (no search log entries); no ISM
    policy is attached to any logs-* index (verified via
    `_plugins/_ism/explain/logs-*`).
  - Passing: `JVMHeapPressure` Average = 41% (heap is not the
    issue); `_cluster/health` `status: yellow` (primaries are
    allocated, no data loss); no `EsRejectedExecutionException`
    in the application logs (thread pools not saturated).
REMEDIATION:
  1. Free disk immediately by deleting the oldest 6 months of
     unqueried indices (enumerated explicitly; no wildcards):
     DELETE /logs-2023-02,logs-2023-03,logs-2023-04,logs-2023-05,logs-2023-06,logs-2023-07
  2. Verify disk drops below flood (95%) on data-3; the
     read-only block auto-clears within ~1-5 minutes once all
     nodes are below flood.
  3. If the block does not auto-clear within 5 minutes of disk
     dropping below flood, force-clear via:
     PUT _all/_settings {"index.blocks.read_only_allow_delete": null}
  4. Long-term: attach an ISM policy to the `logs-*` template
     that rolls indices to UltraWarm at 30 days and deletes at
     12 months. Without this the disk pressure recurs within
     days.
CONFIRM: Before deleting indices or clearing the block, emit and
  await: "CONFIRM: About to delete logs-2023-02 through
  logs-2023-07 on prod-logs-cluster. Proceed? (yes/no)"
  Do NOT run the DELETE until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished flood-stage from high and low watermarks.** A
   generic assistant says "free disk." The skill recognises that
   the `FORBIDDEN/12/index read-only / delete admin api` error
   string is specifically the **flood_stage** (95%) block — not
   the high watermark (90%) and not the low (85%). The diagnostic
   implication: writes are blocked cluster-wide, but the high
   watermark evacuation on the other two nodes is also active
   (they are at 91% and 88%), driving extra IOPS and CPU that
   compound the incident.

2. **Named the upstream cause, not just the symptom.** The
   flood-stage block is the symptom; the upstream cause is
   unbounded index growth (427 monthly indices, no ISM policy).
   A generic assistant stops at "free disk" — the cluster
   re-triggers within days.

3. **Ruled out heap pressure with positive evidence.** A common
   misdiagnosis on `ClusterBlockException` is "raise the heap."
   The skill's `JVMHeapPressure Average = 41%` evidence rules out
   heap pressure with positive evidence before recommending
   disk-action.

4. **Recommended explicit index enumeration, no wildcards.** A
   generic assistant may suggest `DELETE /logs-2023-*` — a typo in
   the wildcard deletes everything. The skill enumerates each
   index in the DELETE call.

5. **Force-clear only as a fallback.** The skill recommends the
   block auto-clear once disk drops below flood — force-clear via
   `_settings` is fallback only, and only after disk is below 95%
   (force-clearing while disk is still above flood causes the
   block to immediately re-apply).

## Slash-command invocation

```
/aws:troubleshoot-opensearch-cluster
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why prod-logs-cluster returns ClusterBlockException"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: opensearch-cluster-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the cluster recovery:

```bash
# Confirm the block cleared
curl -sS "https://<domain-endpoint>/_cluster/health?pretty" \
  -H "Content-Type: application/json"
# Look for status: yellow or green (not red); writes succeed

# Confirm disk drops below 85% (low watermark) for full recovery
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=prod-logs-cluster Name=ClientId,Value=<account> \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Minimum \
  --profile default --output json

# Confirm ISM policy attached to the logs-* template
curl -sS "https://<domain-endpoint>/_index_template/logs-template?pretty" \
  -H "Content-Type: application/json"
```

Then monitor the cluster's `ClusterIndexWritesBlocked` metric for
1-2 hours to confirm the block does not re-trigger.
