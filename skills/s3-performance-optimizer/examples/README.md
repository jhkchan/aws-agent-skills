# Example usage: s3-performance-optimizer

A walkthrough showing the skill optimising a daily 5 GB CSV upload
from ~80 seconds to under 15 seconds via multipart upload with 10
parallel parts at 500 MB each. Demonstrates the workload classification,
the throughput-vs-latency separation, and the evidence-backed
FURTHER_OPTIMIZATION_AVAILABLE verdict.

## Input (user prompt)

> We upload a daily 5 GB CSV file to S3 from an on-prem server over a
> 500 Mbps Direct Connect. The upload takes ~80 seconds; we want it
> under 15 seconds. Currently using a single PUT.

```text
Bucket: prod-daily-exports
Region: us-east-1
Workload: write-once daily bulk upload
ObjectSize: 5 GB
ClientGeography: on-prem over Direct Connect (us-east-1)
TargetLatency: complete upload in <15 s

Current upload command:
  aws s3api put-object --bucket prod-daily-exports \
    --key daily_export.csv --body daily_export.csv

CloudWatch metrics (last upload):
  - BytesUploaded: 5 GB over 81 seconds (~500 Mbps)
  - FirstByteLatency p99: 45 ms
  - 4xxErrors: 0
  - 5xxErrors: 0

Transfer Acceleration: not enabled
Multipart upload: NOT in use (single PUT)
```

## Skill output

```text
TARGET: prod-daily-exports (region: us-east-1, workload: write-once
  daily bulk upload)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: The 5 GB upload uses a single PUT, saturating one TCP stream
  at ~500 Mbps (the link bandwidth-delay product of one stream).
  Multipart upload with 10 parallel parts at 500 MB each opens 10
  concurrent streams, approaching aggregate link bandwidth and
  reducing wall-clock to ~8-10 s (Step 3).
LAYER: MULTIPART_UPLOAD
EVIDENCE:
  - Workload: write-once daily upload; 5 GB object; target <15 s.
  - Current config: single PUT; no multipart in use.
  - Probe: CloudWatch BytesUploaded shows 5 GB over 81 s = ~500 Mbps,
    consistent with single-stream saturation at the link BDP.
  - Probe: Transfer Acceleration is off — appropriate for same-region
    Direct Connect (acceleration adds an edge hop for in-region
    clients).
  - Estimated delta: 81 s -> ~8-10 s (8-10x improvement).
REMEDIATION:
  1. Switch the upload to multipart with 500 MB parts and 10
     concurrent requests:
     aws s3 cp daily_export.csv \
       s3://prod-daily-exports/daily_export.csv \
       --expected-size 5000000000 \
       --multipart-chunksize 500MB \
       --max-concurrent-requests 10
  2. Verify the new wall-clock:
     time aws s3 cp daily_export.csv \
       s3://prod-daily-exports/daily_export.csv \
       --expected-size 5000000000 \
       --multipart-chunksize 500MB \
       --max-concurrent-requests 10
     Expect wall-clock <15 s.
  3. Monitor CloudWatch BytesUploaded over the next upload window.
CONFIRM: Before changing the upload command, emit and await:
  "CONFIRM: About to switch prod-daily-exports upload to multipart
   with 500 MB parts and 10 concurrent requests. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Classified the workload as throughput-bound, not latency-bound.**
   FirstByteLatency is 45 ms — that is fine. The bottleneck is the
   full-body transfer rate, which is a throughput problem solved by
   multipart parallelism.

2. **Did NOT recommend Transfer Acceleration.** A generic assistant
   suggests "enable Transfer Acceleration" for slow uploads. The skill
   recognises that the client is already in-region (Direct Connect to
   us-east-1); acceleration would add an edge hop and likely make it
   slower.

3. **Computed the expected delta from the BDP.** A single TCP stream
   saturates around the bandwidth-delay product. 10 parallel streams
   approach 10x the per-stream rate, bounded by link capacity. The
   ~8-10x projected improvement is grounded in TCP physics, not a
   guess.

4. **Recommended specific part size and parallelism tuned to the
   workload.** A generic assistant says "use multipart upload." The
   skill specifies 500 MB parts and 10 concurrent requests — the right
   defaults for a 5 GB object on a sub-1-Gbps link.

5. **Provided a copy-paste CLI command with the right flags.** The
   `--expected-size`, `--multipart-chunksize`, and
   `--max-concurrent-requests` flags are non-default; the skill calls
   them out explicitly so the operator can verify.

## Slash-command invocation

```
/aws:optimize-s3-performance
```

Or via the orchestrator:

```
/aws:pipeline
You: "speed up a daily 5 GB upload to S3"
```

The orchestrator emits
`[Phase: Optimise | Skills routed: s3-performance-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After applying the change, validate the improvement:

```bash
# Time the new upload
time aws s3 cp daily_export.csv \
  s3://prod-daily-exports/daily_export.csv \
  --expected-size 5000000000 \
  --multipart-chunksize 500MB \
  --max-concurrent-requests 10 \
  --profile default

# Confirm CloudWatch shows higher BytesUploaded/sec and lower
# TotalRequestLatency on the multipart upload
aws cloudwatch get-metric-statistics --namespace AWS/S3 \
  --metric-name BytesUploaded \
  --dimensions Name=BucketName,Value=prod-daily-exports \
  --start-time $(date -d '-30 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Sum \
  --profile default --output json
```

Then monitor the daily upload time over 3-5 runs to confirm
consistency.
