# End-to-End Example: Glue Crawler Deployment

A walkthrough showing how to use the `glue-crawler-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Glue Crawler for S3 event data with a custom
JSON classifier, partition projection, and incremental crawl. The
crawler needs:

- S3 data source: s3://my-data-lake/events/year=2026/
- Custom JSON classifier: EventsJsonClassifier ($.events[*])
- Partition projection: year, month, day
- Database: analytics_db
- Incremental crawl
- Schedule: daily at 2 AM UTC
- Table prefix: raw_
- Tags: Environment=production, DataSource=s3-events

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-glue-crawler
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Glue Crawler for S3 data at
      s3://my-data-lake/events/year=2026/. JSON files with event_id,
      timestamp, event_type, payload. Custom JSON classifier
      EventsJsonClassifier. Partition projection for year/month/day.
      Database analytics_db. Incremental crawl. Daily at 2 AM UTC."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a glue crawler"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
GLUE_CRAWLER: events-crawler (S3: s3://my-data-lake/events/)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Crawler name: events-crawler
  [✓] Data source: S3 (s3://my-data-lake/events/year=2026/)
  [✓] IAM role: GlueCrawlerRole (trust: glue, scoped: my-data-lake/events/*)
  [✓] Classifiers: ["EventsJsonClassifier"] (first-match-wins)
  [✓] Schema merge policy: MergeNewColumns
  [✓] Partitioning: partition-projection (year, month, day)
  [✓] Lake Formation: disabled
  [✓] Catalog database: analytics_db
  [✓] Schedule: cron(0 2 * * ? *) (daily at 2 AM UTC)
  [✓] Crawl mode: incremental
  [✓] Table prefix: raw_
  [✓] Tags: Environment=production, DataSource=s3-events
VERIFICATION_COMMANDS:
  aws glue get-crawler --name events-crawler
  aws glue get-table --database-name analytics_db --name raw_events
  aws glue get-classifier --name EventsJsonClassifier
```

---

## Step 3 — Provisioning commands

### Create the custom JSON classifier

```bash
aws glue create-json-classifier \
  --name "EventsJsonClassifier" \
  --json-path "$.events[*]"
```

### Create the IAM role (if not existing)

```bash
aws iam create-role \
  --role-name GlueCrawlerRole \
  --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy \
  --role-name GlueCrawlerRole \
  --policy-name GlueCrawlerPermissions \
  --policy-document file://permissions-policy.json
```

### Create the crawler

```bash
aws glue create-crawler \
  --name events-crawler \
  --role GlueCrawlerRole \
  --database-name analytics_db \
  --classifiers EventsJsonClassifier \
  --table-prefix raw_ \
  --targets '{"S3Targets":[{"Path":"s3://my-data-lake/events/year=2026/"}]}' \
  --schedule "cron(0 2 * * ? *)" \
  --recrawl-policy '{"RecrawlBehavior":"CRAWL_INCREMENTAL"}' \
  --configuration '{"Version":1.0,"CrawlerOutput":{"Tables":{"AddOrUpdateBehavior":"MergeNewColumns"}}}' \
  --tags Environment=production,DataSource=s3-events
```

### Start the first crawl (always full)

```bash
aws glue start-crawler --name events-crawler
```

### Configure partition projection on the table (post-crawl)

```bash
aws glue update-table \
  --database-name analytics_db \
  --table-input '{
    "Name": "raw_events",
    "StorageDescriptor": { "Location": "s3://my-data-lake/events/" },
    "PartitionKeys": [
      { "Name": "year", "Type": "int" },
      { "Name": "month", "Type": "int" },
      { "Name": "day", "Type": "date" }
    ],
    "Parameters": {
      "projection.enabled": "true",
      "projection.year.type": "integer",
      "projection.year.range": "2024,2026",
      "projection.month.type": "integer",
      "projection.month.range": "01,12",
      "projection.month.digits": "2",
      "projection.day.type": "date",
      "projection.day.format": "yyyy-MM-dd",
      "projection.day.range": "2024-01-01,NOW",
      "storage.location.template": "s3://my-data-lake/events/year=${year}/month=${month}/day=${day}"
    }
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# Crawler status
aws glue get-crawler --name events-crawler

# Table created by the crawler
aws glue get-table --database-name analytics_db --name raw_events

# Classifier
aws glue get-classifier --name EventsJsonClassifier

# Query with Athena
aws athena start-query-execution \
  --query-string "SELECT * FROM analytics_db.raw_events WHERE year=2026 AND month='08' LIMIT 10" \
  --query-execution-context Database=analytics_db \
  --result-configuration OutputLocation=s3://my-athena-results/
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Classifier order | No custom classifier | EventsJsonClassifier listed first | Built-in JSON classifier would guess schema; custom JSON path is precise |
| Partition strategy | Folder enumeration | Partition projection | Eliminates GetPartitions cost for date-range partitions |
| Crawl mode | Full crawl | Incremental crawl | 10-100x faster for append-only data |
| IAM scoping | Resource: * | Scoped to specific bucket/path | Least-privilege prevents reading unintended data |
| Lake Formation | Not checked | LF permissions verified | LF-enabled DB requires crawler role grants |
| First crawl | Incremental assumed | First crawl is always full | Incremental requires prior state |

---

## Related artifacts

- **Skill definition:** `skills/glue-crawler-deployer/SKILL.md`
- **Classifiers and partitioning guide:** `skills/glue-crawler-deployer/references/classifiers-and-partitioning.md`
- **IAM and Lake Formation guide:** `skills/glue-crawler-deployer/references/iam-and-lake-formation.md`
- **Slash command:** `commands/aws/deploy-glue-crawler.md`
- **Eval suite:** `skills/glue-crawler-deployer/evals/evals.json`
- **Legacy test cases:** `skills/glue-crawler-deployer/eval/test-cases.yaml`
