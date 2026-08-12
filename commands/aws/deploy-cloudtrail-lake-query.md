---
description: Provision AWS CloudTrail Lake with production-grade defaults (event data store creation, event type selection, advanced event selectors, SQL forensic querying, data protection PII masking, multi-account Organization EDS, retention management, Athena federation). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "cloudtrail lake"
  - "event data store"
  - "cloudtrail lake query"
  - "cloudtrail eds"
  - "cloudtrail forensic"
  - "athena federation cloudtrail"
  - "cloudtrail data protection"
  - "multi-account cloudtrail lake"
  - "cloudtrail lake eds"
  - "eds creation"
routes_to: cloudtrail-lake-query-deployer
---

# /aws:deploy-cloudtrail-lake-query

Activate the `cloudtrail-lake-query-deployer` skill and provision AWS
CloudTrail Lake with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. CloudTrail Lake vs standard trails (key differences)
2. Event data store creation (EDS type is immutable)
3. Event ingestion (management, data, Insights)
4. Advanced event selectors (fine-grained data event filtering)
5. SQL query (StartQuery + GetQueryResults)
6. Forensic query patterns (who deleted X, what did user Y do)
7. Multi-account EDS via Organizations
8. Retention and billing (per-GB ingested + per-GB scanned)
9. Data protection (PII masking before query results)
10. Athena federation and CloudWatch integration

## When to use

- You need a CloudTrail Lake event data store for SQL querying.
- You need forensic query capability (who deleted a resource).
- You need data protection (PII masking) on CloudTrail events.
- You need multi-account event ingestion via Organizations.
- You need advanced event selectors for data events.
- You need Athena federation for CloudTrail Lake.

## When NOT to use

- **Standard CloudTrail trails** — use cloudtrail skills for S3-based
  trails.
- **CloudWatch Logs** — use cloudwatch skills for log groups.
- **AWS Config** — use config skills for configuration compliance.
- **Security Hub** — use security-hub skills for security findings.

## How to invoke

### Slash command

```
/aws:deploy-cloudtrail-lake-query
```

Then provide: EDS name, event type (management/data/Insights),
retention period, data protection requirements, multi-account scope,
selector details (for data events), tags.

### Natural language

Any of these routes to the same skill:

- "create a cloudtrail lake event data store"
- "set up cloudtrail lake for forensic queries"
- "configure cloudtrail lake data protection"
- "create a multi-account cloudtrail lake eds"
- "enable cloudtrail lake with athena federation"

### CLI routing

```bash
node cli/bin/cli.js route "create cloudtrail lake eds"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create CloudTrail
Lake infrastructure for event querying and forensics. The output
checklist feeds into verification pipelines and downstream governance
skills.

## Example

```
You: /aws:deploy-cloudtrail-lake-query

     Create a CloudTrail Lake EDS for management events. 90-day
     retention. Mask email and phone PII.

Skill:
  CLOUDTRAIL_LAKE: mgmt-events-eds
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Event type: Management events
    [✓] Retention: 90 days
    [✓] Data protection: EmailAddress, PhoneNumber masked
    [✓] Query API: cloudtrail-data (StartQuery + GetQueryResults)
    [✓] Billing: $0.75/GB ingested + $0.005/GB scanned
  VERIFICATION_COMMANDS:
    aws cloudtrail list-event-data-stores
```

## References

- Skill definition: `skills/cloudtrail-lake-query-deployer/SKILL.md`
- Querying guide: `skills/cloudtrail-lake-query-deployer/references/querying-and-forensics.md`
- EDS guide: `skills/cloudtrail-lake-query-deployer/references/eds-and-multi-account.md`
- Eval suite: `skills/cloudtrail-lake-query-deployer/evals/evals.json`
