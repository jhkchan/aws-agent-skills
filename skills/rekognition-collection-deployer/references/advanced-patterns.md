# Advanced Patterns — Rekognition Collection Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

- **"The default similarity threshold is fine."** The API default is
  80%, but operators pass lower thresholds (50-60%) to get more
  matches. This produces false positives at scale. For production face
  matching, 80%+ is the minimum; below 80%, false positive rates rise
  significantly as collection size grows.

- **"Collections scale infinitely."** A single collection supports up
  to 50 million faces, but search latency degrades as face count grows.
  At 1M+ faces, consider partitioning by region or category into
  multiple collections. Index-faces and search-faces-by-image also
  share the same TPS quota.

- **"The stream processor handles scaling."** The stream processor
  reads from Kinesis shards. Throughput is bounded by shard count.
  Shard-level parallelism is the scaling lever — more shards = more
  parallel face searches. A single shard limits the processor to one
  concurrent consumer.


## Configuration dependency graph (sequencing notes)

Rekognition configurations are NOT independent. The collection must
exist before faces are indexed. Faces must be indexed before they can
be searched. The stream processor needs BOTH a Kinesis input stream
and a Kinesis output stream. KMS encryption must be configured at
collection creation time (not retroactively). Custom labels models
must be trained before they can be started.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Collection | KMS key (if encrypted); IAM `rekognition:CreateCollection` | KMS encryption CANNOT be added after creation | face indexing, face search |
| Face indexing | Collection exists; image in S3 or bytes | FaceId is server-generated; ExternalImageId recommended for traceability | face search by FaceId |
| Face search (by image) | Collection has indexed faces; IAM `rekognition:SearchFacesByImage` | similarity threshold below 80% produces false positives at scale | face matching results |
| Stream processor | Kinesis input stream; Kinesis output stream; IAM role with all three permissions | shard count determines parallelism; missing any IAM permission causes silent failure | real-time video face detection |
| Content moderation | IAM `rekognition:DetectModerationLabels` | works without a collection | unsafe content flags |
| Custom labels model | S3 training data; IAM role; dataset labeled | model MUST be started (start-project-version) after training; inference costs accrue hourly | custom label inference |
| KMS encryption | KMS key with proper key policy | CANNOT be added after creation — MUST be set at create time | encryption at rest |
| SNS notification | SNS topic; IAM role with `sns:Publish` | only async (Start*) operations support SNS | async job completion callbacks |

**The KMS-at-creation row is the one a baseline model misses.** KMS
encryption cannot be added to an existing collection. If encryption is
required (compliance, GDPR, HIPAA), the KMS key ID MUST be specified at
`create-collection` time. Re-creating an encrypted collection means
re-indexing all faces.

**Cross-dependency gotchas:**
- The stream processor needs a Kinesis data stream (not Kinesis Video
  Stream). Each record is a base64-encoded JPEG frame.
- Face indexing and search share the same TPS quota. Heavy indexing
  throttles search. Plan indexing during off-peak hours.
- Custom labels models incur hourly charges while running. Stop the
  model when not in use.
- SNS notifications only work with async (Start*) operations, not
  synchronous (Detect*, Search*) operations.


## Expert heuristic: similarity threshold 80%+ for face matching

A baseline model says "search faces with the default threshold." The
correct heuristic recognizes that threshold tuning is the single most
important quality lever in production face matching.

```text
Similarity threshold guide:
  99%+   → near-exact (identity verification, access control)
  90-99% → strict matching (badge systems, attendance)
  80-90% → production-grade (balanced; recommended default)
  60-80% → loose matching (human-in-the-loop review only)
  <60%   → NOT recommended (false positives dominate)

Collection size impact on accuracy:
  <10k faces      → 80% threshold is reliable
  10k-100k faces  → 80% recommended; consider 85% for tighter matching
  100k-1M faces   → 85%+ recommended; false positive rate rises
  1M-10M faces    → 90%+ recommended; consider collection partitioning
  10M+ faces      → MUST partition into multiple collections
```

**Key implication:** the threshold is not "set and forget." As the
collection grows, the threshold may need to increase to maintain the
same false-positive rate.


## Expert heuristic: stream processor shard-level parallelism

The stream processor reads from Kinesis shards. Each shard is processed
by one consumer. More shards = more parallel face searches = higher
throughput.

```text
Stream processor throughput scaling:
  Input Kinesis stream shard count:
    1 shard  → 1 concurrent face search
    4 shards → 4 concurrent face searches
    N shards → N concurrent face searches (linear scaling)

  Output Kinesis stream:
    Needs enough shards to absorb output rate
    If output is throttled, processor backs up

  Typical production setup:
    Input: 4-8 shards (camera feeds at 1-5 fps per camera)
    Output: 2-4 shards (match results, smaller payloads)
```

**Key implication:** the processor's throughput is NOT configurable via
the Rekognition API — it is determined entirely by the input Kinesis
stream's shard count.


## Expert heuristic: collection face count scaling

A baseline model says "one collection for everything." The correct
heuristic recognizes that search latency and false positive rates
degrade as face count grows. Partitioning strategy should be decided
BEFORE indexing begins.

```text
Collection size decision tree:
  <1M faces    → single collection is fine; threshold 80%+
  1M-10M faces → single collection works; increase threshold to 85-90%
  10M+ faces   → MUST partition by region/category; 90%+ threshold
  Multi-region → partition by region for data residency + latency
```
