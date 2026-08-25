# Advanced Patterns (load on demand) — Data Exchange Dataset Deployer

Mindset misconceptions, the configuration dependency graph, expert
heuristics (auto-export orchestration, entitlement-vs-IAM, asset-type
export semantics), and Recent AWS features moved verbatim from SKILL.md.
Loaded on demand.

---

## Mindset — the three misconceptions (moved from SKILL.md)



**One-line takeaway:** AWS Data Exchange is a marketplace for data
products. A subscription grants access to a data set. Revisions are
versioned snapshots of the data — each revision contains assets (S3
objects, DynamoDB table exports, API endpoints). Auto-export
(EventBridge rule) triggers an export job when a new revision is
published, automatically delivering fresh data to your S3 bucket.
Entitlements are the sharing mechanism — NOT IAM. Lake Formation
integration provides governed, fine-grained access to the exported
data.

Three misconceptions dominate Data Exchange misdesign at provisioning
time:

- **"IAM policies control data access."** They do NOT for Data
  Exchange sharing. Entitlements are the sharing mechanism. A data
  set is shared with a specific AWS account via an entitlement, not
  via IAM role trust or bucket policy. The receiving account accesses
  the data through the Data Exchange API or auto-export, not through
  direct S3 access. IAM controls who can call Data Exchange APIs,
  but entitlements control which data sets an account can access.

- **"Revisions auto-export by default."** They do NOT. By default,
  when a provider publishes a new revision, the subscriber must
  manually trigger an export job to get the new data. Auto-export
  requires an EventBridge rule that triggers on the
  "Data Update" event from Data Exchange, which then calls
  StartJob to export the new revision to the subscriber's S3 bucket.
  Without this rule, new revisions sit in Data Exchange and are
  never delivered to the subscriber's analytics pipeline.

- **"Export jobs are synchronous."** They are NOT. Export jobs are
  asynchronous — they run in the background and can take minutes to
  hours depending on data volume. The job status transitions from
  PENDING to IN_PROGRESS to COMPLETED (or ERROR). Polling job status
  via GetJob or monitoring via EventBridge/CloudWatch is required.
  Scripts that start a job and immediately try to read the exported
  data will fail.



## Configuration dependency graph (moved from SKILL.md)



Data Exchange configurations are NOT independent. The subscription
must exist before revisions are visible. Revisions must be finalized
before assets can be exported. Auto-export rules must reference the
correct job definition. Entitlements must be set before the receiving
account can access the data set. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subscription | data product exists in marketplace; subscriber account approved | subscription terms accepted at creation; cannot be partially scoped | access to data set revisions |
| Data set | subscription active; data set ID known | data set belongs to the provider; subscribers cannot modify the data set | revisions |
| Revision | data set exists; revision created by provider | revision must be FINALIZED before assets can be exported; drafts are invisible to subscribers | asset export |
| Assets | revision exists; asset type matches export destination | S3 snapshot assets export to S3; API assets are accessed live (not exported); DynamoDB exports as S3 objects | export job |
| Export job | revision FINALIZED; destination S3 bucket exists; IAM role with s3:PutObject | job is ASYNCHRONOUS; polling required; job definition specifies mapping of assets to S3 keys | data in subscriber S3 |
| Auto-export rule | EventBridge rule on "Data Update" event; Lambda or Step Functions to call StartJob | auto-export does NOT exist by default; must be explicitly configured; wrong job definition = silent failure | automatic data delivery on new revisions |
| Entitlement | data set exists; target AWS account ID known; entitlement created by provider (or via product) | entitlement is the SHARING mechanism — not IAM; receiving account cannot access without entitlement; target account must accept | data sharing across accounts |
| Lake Formation | exported data in S3; Lake Formation enabled; Data Catalog database/table created | LF grants control column/row-level access; without LF, IAM bucket policy is the only access control | governed, fine-grained data access |
| API asset | subscription active; API asset type in data set | API assets are accessed LIVE via Data Exchange API gateway; NOT exported to S3; auth via Data Exchange credentials | REST endpoint data consumption |

**The auto-export-rule row is the one a baseline model misses.**
Without an EventBridge auto-export rule, new revisions are published
but never delivered to the subscriber's S3 bucket. The data sits in
Data Exchange and the subscriber never knows a new revision arrived.
The procedure below forces an explicit decision on auto-export.

**Cross-dependency gotchas:**
- Export jobs are asynchronous. Scripts that start a job and
  immediately read from the destination S3 bucket will fail. Poll
  job status or use EventBridge to trigger downstream processing
  only after job completion.
- Entitlements are the sharing mechanism, NOT IAM. Adding IAM
  policies for the receiving account does NOT grant access to the
  data set. The provider must create an entitlement for the target
  account.
- API assets are accessed LIVE through the Data Exchange API
  gateway — they are NOT exported to S3. S3 auto-export rules do
  not apply to API assets.
- Lake Formation grants apply to the exported data in the Data
  Catalog, not to Data Exchange itself. LF integration requires the
  data to be exported to S3 first, then registered as a LF-managed
  table.
- Revision finalization is a one-way operation. Once finalized, a
  revision cannot be modified. All assets must be added BEFORE
  finalization.



## Expert heuristic: auto-export revision rule (moved from SKILL.md)



A baseline model says "subscribe and export." The correct heuristic
recognizes that auto-export is a separate EventBridge-triggered
workflow that must be explicitly configured.

```text
Auto-export flow:
  1. Provider publishes new revision (finalize + publish)
  2. EventBridge emits "Data Update" event
     → Event source: aws.dataexchange
     → Detail type: Data Update
     → Contains: data set ID, revision ID
  3. EventBridge rule matches the event
     → Routes to Lambda / Step Functions target
  4. Lambda calls StartJob with:
     → Job type: EXPORT_ASSETS_TO_S3
     → Revision ID from the event
     → Destination S3 bucket (subscriber's)
     → Asset-to-key mapping
  5. Export job runs asynchronously
     → Status: PENDING → IN_PROGRESS → COMPLETED
  6. Data appears in subscriber's S3 bucket
  7. Downstream EventBridge/Step Functions triggered by S3 PUT

Without steps 2-4: revision sits in Data Exchange, never delivered.
```

**Key implication:** auto-export is NOT a Data Exchange feature
that you toggle on. It is an EventBridge + Lambda orchestration
that you build. The skill provides the template for this
orchestration.



## Expert heuristic: entitlement is the sharing mechanism (moved from SKILL.md)



A baseline model says "share via IAM role." The correct heuristic
recognizes that entitlements control data set access across
accounts.

```text
Sharing decision tree:
  ├── Provider shares with subscriber → entitlement (provider creates)
  │     └── Subscriber accepts → accesses data via Data Exchange API or auto-export
  ├── Internal account sharing → Lake Formation grants (after export to S3)
  │     └── LF controls column/row-level access for IAM principals
  └── Cross-account S3 access (post-export) → S3 bucket policy or cross-account IAM
        └── This is for the EXPORTED data only, not the Data Exchange data set

Entitlement vs IAM:
  Entitlement: "Account X is allowed to access data set Y"
  IAM:         "Principal Z is allowed to call dataexchange:StartJob"
  Both needed: entitlement (what you can access) + IAM (what you can call)
```

**Key implication:** to share a Data Exchange data set with another
account, create an entitlement. IAM alone does not grant data set
access.



## Expert heuristic: asset types determine export behavior (moved from SKILL.md)



A baseline model says "export the data." The correct heuristic
recognizes that different asset types have different export behavior.

```text
Asset type → Export behavior:
  S3_SNAPSHOT  → Exported to subscriber's S3 bucket as objects
                  Export job copies S3 objects from provider to subscriber
                  Mapping: asset name → S3 key prefix

  REDSHIFT_SNAPSHOT → Exported as Redshift snapshot (must have Redshift cluster)
                       NOT exported to S3

  API         → Accessed LIVE via Data Exchange API gateway
                NOT exported to S3
                Auth via Data Exchange signing key
                Rate-limited per entitlement

  QUERY       → Lake Formation-backed SQL query results
                Requires LF integration
                Results exported to S3
```

**Key implication:** S3 auto-export works for S3_SNAPSHOT assets.
API assets are consumed live and cannot be auto-exported. Redshift
snapshots require a Redshift cluster.



## Recent AWS features (2023-2026) (moved from SKILL.md)



**Recent AWS features (2023-2026):**

- **Data Exchange for Amazon S3 (2023-2024):** Direct S3 access for
  subscribed data products without manual export jobs. Subscribers
  can read directly from the provider's S3 bucket via Data Exchange-
  managed access, eliminating the need for export job orchestration.

- **Data Exchange API assets (2023-2024):** Providers can now offer
  REST API endpoints as data products. Subscribers access live data
  via authenticated API calls, enabling real-time data consumption
  without export latency.

- **Lake Formation fine-grained access control (2023-2024):**
  Enhanced integration between Data Exchange and Lake Formation
  enables column-level and row-level access control on exported
  data, supporting multi-tenant analytics with per-tenant visibility
  rules.

- **EventBridge auto-export templates (2023-2024):** AWS introduced
  pre-built EventBridge + Lambda templates for auto-export, reducing
  the setup overhead for subscribers who want automatic data
  delivery.

- **Data Exchange for API Gateway (2024-2025):** Providers can
  monetize API endpoints through Data Exchange, with built-in rate
  limiting, usage tracking, and per-subscriber authentication.

- **CloudWatch dashboards for Data Exchange (2024-2025):** Pre-built
  CloudWatch dashboard templates for monitoring export job health,
  revision freshness, and data volume across subscriptions.

- **Step Functions integration for multi-step exports (2024-2025):**
  Step Functions state machines for orchestrating multi-step export
  pipelines (export → transform → load into Redshift/Athena),
  replacing custom Lambda orchestration.


