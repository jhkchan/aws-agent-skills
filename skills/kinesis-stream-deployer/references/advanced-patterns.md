# Advanced Patterns — kinesis-stream-deployer

Moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Mindset deep-dive — three common misconceptions

Three misconceptions dominate Kinesis stream misdesign at provisioning
time:

- **"I can switch between provisioned and on-demand freely."** You CAN
  switch modes, but frequent switching is throttled (the stream must
  remain in each mode for a minimum of 15 minutes). More importantly,
  the cost model is fundamentally different: provisioned charges per
  shard-hour; on-demand charges per GB ingested plus per stream-hour.
  On-demand is simpler but can cost more for high, steady-state
  throughput.

- **"Enhanced fan-out is just a faster GetRecords."** It is not.
  Enhanced fan-out uses a dedicated HTTP/2 streaming protocol
  (SubscribeToShard) giving each consumer its own 2 MiB/sec read
  throughput — no contention. Standard GetRecords shares a total 2
  MiB/sec read throughput per shard across ALL consumers. Enhanced
  fan-out costs extra (data retrieval fee per consumer-shard-hour).

- **"More shards is always safer."** Provisioned shards cost money per
  shard-hour. Over-provisioning inflates cost without benefit. Size
  shards based on expected write throughput (1 MiB/sec or 1,000
  records/sec per shard) and use on-demand mode if traffic is bursty or
  unpredictable.

## Configuration dependency graph (novel heuristic)

Kinesis stream configurations are NOT independent. Stream mode
determines scaling behavior; shard count is irrelevant in on-demand
mode; encryption must be enabled with a compatible key policy. Use this
graph to sequence provisioning and to debug "why is my consumer
throttled?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Stream mode | none — `create-stream` argument | mode CAN be switched but throttled to once per 15 min; cost model changes | scaling model |
| Shard count | REQUIRED if PROVISIONED; IGNORED if ON_DEMAND | mutable via `update-shard-count` (provisioned only); cannot scale below 1 | write/read throughput (provisioned) |
| Enhanced fan-out consumer | stream must be ACTIVE; name unique per stream | max 20 consumers per stream (soft limit); must re-register if stream deleted/recreated | dedicated 2 MiB/sec read per consumer |
| SSE-KMS encryption | KMS key exists and key policy permits kinesis service | encryption cannot be disabled safely once enabled on the stream | data-at-rest encryption |
| IAM policy (producer) | stream ARN in Resource; `kinesis:PutRecord` action | missing `kinesis:DescribeStream` blocks troubleshooting | write access |
| IAM policy (consumer) | stream ARN in Resource; `kinesis:GetRecords` action | enhanced fan-out needs `kinesis:SubscribeToShard` + consumer ARN | read access |
| Retention period | 24 hours (default) to 8760 hours (365 days) | increasing retention increases cost; decreasing drops data | replay window |
| Stream ARN resource policy | stream exists (latest feature) | replaces cross-account IAM for some read-only patterns | resource-based access control |

**The mode-dependent rows are the ones a baseline model misses.** Shard
count is IGNORED in on-demand mode — specifying it does nothing. Enhanced
fan-out consumer registration requires an ACTIVE stream. SSE-KMS cannot
be safely disabled once enabled. The procedure below forces an explicit
decision on each before the `create-stream` call.

**Cross-dependency gotchas:**
- Enhanced fan-out and standard GetRecords coexist; enhanced consumers
  do NOT consume from the shared 2 MiB/sec read budget.
- SSE-KMS encryption applies to new records going forward.
- Retention period extension increases cost. Reduce only if consumers
  can tolerate a shorter replay window.
- Increasing shard count (provisioned) triggers shard splitting;
  decreasing triggers merging. Both briefly affect throughput.

## Expert heuristic: provisioned vs on-demand cost crossover

A baseline model says "use on-demand for simplicity." The correct
heuristic is to identify the cost crossover point where provisioned
becomes cheaper.

```text
Provisioned cost = shard_count × $0.015/hour (varies by region)
  + per-record PUT cost (negligible for rough sizing)

On-demand cost = ~$0.04/hour per stream (varies by region)
  + ~$0.029 per GB ingested

Rough crossover (write throughput in MiB/sec):
  provisioned_shards = ceil(throughput_mib_per_sec / 1)
  provisioned_hourly = provisioned_shards × $0.015
  on_demand_hourly = $0.04 + (throughput_mib_per_sec × 3600 / 1024 × $0.029)

Rule of thumb:
  ├── Steady, predictable throughput > ~2-3 MiB/sec → provisioned is cheaper
  ├── Bursty / unpredictable / < 1 MiB/sec average → on-demand is cheaper
  └── Unknown traffic → start on-demand, switch to provisioned after 2-4 weeks
```

**Key implication:** on-demand has a per-GB-ingested component that
scales linearly. At high sustained throughput, provisioned shards have a
flat cost. The crossover is typically around 2-4 MiB/sec sustained.

## Expert heuristic: enhanced fan-out vs GetRecords read model

Enhanced fan-out is NOT automatically better. The decision depends on
the number of consumers and latency requirements.

| Pattern | Standard GetRecords | Enhanced fan-out |
|---|---|---|
| 1 consumer | Cheapest — uses the 2 MiB/sec shared budget | Overkill — costs extra for no benefit |
| 2-3 consumers, polling OK | Shared 2 MiB/sec split across consumers | Each gets 2 MiB/sec; lower latency (HTTP/2 push) |
| 4+ consumers, low-latency | Contended throughput; polling overhead | Each gets dedicated 2 MiB/sec; ~70ms typical latency |
| Cost-sensitive | No data-retrieval fee | ~$0.013 per consumer-shard-hour (data retrieval fee) |

```text
Decision tree:
  How many consumers read from this stream?
  ├── 1 consumer → standard GetRecords (no enhanced fan-out cost)
  ├── 2-3 consumers, latency-tolerant → standard GetRecords (shared budget OK)
  ├── 2-3 consumers, low-latency → enhanced fan-out (dedicated push)
  └── 4+ consumers → enhanced fan-out (avoids read contention)
```

## Expert heuristic: IteratorAgeMilliseconds alarm threshold

`GetRecords.IteratorAgeMilliseconds` is the #1 indicator of consumer
health. A baseline model sets a generic alarm; the correct threshold
depends on the retention period and consumer SLA.

```text
IteratorAge = time between the newest record in the shard and
              the position the consumer last read.

Healthy consumer: IteratorAge < 10,000 ms (10 seconds)
Falling behind:   IteratorAge > 60,000 ms (1 minute)
Critical:          IteratorAge > retention_period × 0.8 (data loss imminent)

Alarm strategy:
  ├── Warning: IteratorAge > 300,000 ms (5 min) for 3-5 consecutive periods
  ├── Critical: IteratorAge > (retention_period_ms × 0.5)
  └── Maximum possible IteratorAge = retention period (data loss at that point)
```

**Key implication:** the alarm threshold MUST be relative to the
retention period. A 24-hour retention with a 1-hour IteratorAge alarm is
fine; a 1-hour retention with a 1-hour IteratorAge alarm means data loss
is already happening when the alarm fires.

## Prerequisites (verify before provisioning)

## Step 8 — Stream ARN resource policies (detail)

Recent feature: Kinesis supports stream-level resource-based policies
(similar to S3 bucket policies) for cross-account access.

```bash
aws kinesis put-resource-policy \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "CrossAccountConsumer",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
      "Action": ["kinesis:GetRecords", "kinesis:GetShardIterator",
                  "kinesis:DescribeStreamSummary", "kinesis:ListShards"],
      "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream"
    }]
  }' --region us-east-1
```

For cross-account access, EITHER a stream resource policy OR an IAM role
in the stream's account that the consumer assumes. Resource policies are
simpler for read-only consumer patterns. For same-account access, IAM
identity-based policies are sufficient.


## Step 9 — Recent features (detail)

**Recent AWS features (2023-2026):**

- **Kinesis on-demand capacity mode (2021-2023, broadly adopted):**
  Auto-scales write capacity without shard management. Scales to
  accommodate up to 200% of the prior 30 minutes' peak. Cost is
  per-GB-ingested plus per-stream-hour.
- **Kinesis Stream ARN resource policies (2023-2024):** Stream-level
  resource-based policies for cross-account/cross-service access control.
- **SubscribeToShard HTTP/2 maturity (enhanced fan-out):** Up to 20
  consumers per stream, ~70ms typical latency via server-push.
- **Capacity limits API (2023-2024):** `DescribeStreamSummary` exposes
  `ConsumerCount` for capacity planning.
- **TLS 1.2 enforcement (2024-2025):** Kinesis now enforces TLS 1.2
  minimum for all API connections.
- **update-shard-count improvements (2023-2024):** Smoother shard
  splitting/merging with reduced impact on in-flight records.

