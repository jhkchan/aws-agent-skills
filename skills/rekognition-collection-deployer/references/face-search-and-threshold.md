# Face Search and Similarity Threshold — Rekognition Collection Deployer

Deep reference on face search mechanics (search by image vs search by
FaceId), similarity threshold tuning for production accuracy, collection
size impact on search quality, and partitioning strategies for scale.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Face search modes

### Search faces by image

`search-faces-by-image` takes a query image, extracts the largest face,
and searches the collection for similar faces.

```bash
aws rekognition search-faces-by-image \
  --collection-id "employee-faces" \
  --image '{"S3Object":{"Bucket":"my-bucket","Name":"query.jpg"}}' \
  --face-match-threshold 80 \
  --max-faces 5 \
  --region us-east-1
```

**Limitation:** if the image contains multiple faces, Rekognition uses
the largest face for the search. To search for a specific face, crop
the image first or use `search-faces` with a FaceId.

### Search faces by FaceId

`search-faces` takes an existing FaceId (from a prior `index-faces` or
`search-faces-by-image` call) and finds similar faces in the collection.

```bash
aws rekognition search-faces \
  --collection-id "employee-faces" \
  --face-id "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --face-match-threshold 80 \
  --max-faces 5 \
  --region us-east-1
```

**Use case:** de-duplication. After indexing a new face, search by its
FaceId to find if the same person is already in the collection under a
different FaceId.

## Similarity threshold deep dive

### What the threshold means

The similarity score (0-100) represents the cosine distance between the
query face's feature vector and the indexed face's feature vector.
Higher = more similar.

### Threshold selection by use case

| Use case | Recommended threshold | Rationale |
|---|---|---|
| Identity verification (1:1) | 99%+ | Must be nearly exact; high false-negative is acceptable |
| Badge / access control | 90-99% | Low false-positive critical for security |
| Attendance tracking | 85-95% | Balanced; human review for edge cases |
| General production matching | 80-90% | Sweet spot; balanced precision/recall |
| Photo tagging (human-in-loop) | 60-80% | High recall preferred; humans confirm |
| Investigation / lead generation | 50-60% | Cast wide net; all results are leads, not conclusions |

### Collection size impact

As the collection grows, the probability of a random face being similar
enough to trigger a false match increases. The threshold must be tuned
upward as the collection scales.

```text
False positive rate (approximate, at 80% threshold):
  ├── 1k faces      → ~0.1% FPR
  ├── 10k faces     → ~0.5% FPR
  ├── 100k faces    → ~2% FPR
  ├── 1M faces      → ~5% FPR
  └── 10M faces     → ~15% FPR (unacceptable for most use cases)
```

**Rule of thumb:** increase threshold by 5% for every order of
magnitude increase in collection size beyond 10k faces.

### Tuning methodology

1. **Baseline:** start at 80% for a new collection.
2. **Measure:** collect false positive and false negative rates from
   real-world usage over 2-4 weeks.
3. **Adjust:** if false positive rate exceeds the acceptable threshold
   for your use case, increase the threshold by 5% and re-measure.
4. **Monitor:** as the collection grows, periodically re-evaluate.

## Collection partitioning for scale

### When to partition

- Collection exceeds 1 million faces AND search quality degrades.
- Different geographic regions need independent face stores (data
  residency).
- Different use cases (employees vs visitors) need isolation.

### Partitioning strategies

**By region/site:**

```text
Collections:
  ├── employee-faces-us-east  (US East Coast offices)
  ├── employee-faces-us-west  (US West Coast offices)
  ├── employee-faces-eu       (European offices)
  └── employee-faces-apac     (APAC offices)
```

**By category:**

```text
Collections:
  ├── employee-faces       (employees)
  ├── contractor-faces     (contractors)
  ├── visitor-faces        (visitors)
  └── blocklist-faces      (denied persons)
```

**By hash (for uniform distribution):**

```text
Collections:
  ├── faces-shard-0   (FaceIds hashed to shard 0)
  ├── faces-shard-1   (FaceIds hashed to shard 1)
  ├── faces-shard-2   (FaceIds hashed to shard 2)
  └── faces-shard-3   (FaceIds hashed to shard 3)
```

With hash-based partitioning, the application must search ALL shards for
a face search (since the query image's FaceId is not known in advance).

## Face lifecycle management

### Deleting faces

```bash
aws rekognition delete-faces \
  --collection-id "employee-faces" \
  --face-ids "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" \
  --region us-east-1
```

Use when an employee leaves or a face was indexed in error.

### Listing faces

```bash
aws rekognition list-faces \
  --collection-id "employee-faces" \
  --max-results 100 \
  --region us-east-1
```

Use for auditing and collection inventory.

## Terraface examples

```hcl
# Create a Rekognition collection with KMS encryption
resource "aws_rekognition_collection" "employee_faces" {
  collection_id = "employee-faces"
  kms_key_id    = aws_kms_key.rekognition.arn

  tags = {
    Environment = "production"
    UseCase     = "employee-access"
  }
}
```
