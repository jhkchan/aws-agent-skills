# Advanced Patterns (load on demand) — Amazon DataZone Domain Deployer

Mindset misconceptions, the configuration dependency graph, and Recent
AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset — the three misconceptions (moved from SKILL.md)



**One-line takeaway:** Amazon DataZone is a data management service
that lets you catalog, govern, and share data across accounts and
teams. The domain is the top-level container; projects organize users
and data sources; subscriptions govern who can access what via a
request-approve model. Cross-account data access requires IAM role
chaining — the DataZone domain account assumes a role in the data
source account to read data. Glossary terms drive governance: assets
tagged with glossary terms inherit subscription policies.

Three misconceptions dominate DataZone misdesign at provisioning time:

- **"Creating the domain is enough to share data."** It is not. The
  domain is the container. To share data, you need: (1) a project with
  a data source connection, (2) the data source account must have an
  IAM role that DataZone can assume, (3) a subscription must be
  requested and approved. Creating the domain alone does nothing for
  data access. The cross-account IAM role chain is the #1 forgotten
  step.

- **"Subscriptions are automatically approved."** They are NOT by
  default. DataZone uses a request-approve model: a consumer requests
  access to an asset, and a project owner (or delegated approver)
  must approve the request. This is by design — it enforces data
  governance. Auto-approval can be configured but defeats the purpose
  of subscription governance.

- **"Glossary terms are just labels."** They are the governance
  mechanism. Glossary terms can carry subscription policies: an asset
  tagged "PII" might require the project owner's approval, while an
  asset tagged "Public" might allow auto-approval. The glossary is
  the policy engine, not just a labeling system. A baseline model
  treats glossary as cosmetic; it is structural.



## Configuration dependency graph (moved from SKILL.md)



DataZone configurations are NOT independent. The domain must exist
before projects. Projects must exist before data sources. Data
sources require cross-account IAM roles. Subscriptions require assets
to be published. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Domain | AWS account with DataZone available; SSO configured | domain name must be unique; domain ARN is the root for all resources | project creation |
| Project | domain exists | project cannot be deleted if it has active subscriptions — must revoke first | data source, environment, user association |
| Data source (S3) | project exists; S3 bucket in source account; IAM role in source account allowing DataZone to assume | the IAM role in the source account is the #1 missing prerequisite; without it, DataZone cannot read data | asset auto-discovery |
| Data source (Redshift) | project exists; Redshift cluster/serverless namespace; IAM role; secrets manager secret | the Redshift connection requires a Secrets Manager secret for credentials | asset auto-discovery for Redshift |
| Asset | data source configured and crawled | assets are auto-discovered from the data source; they must be published (made visible) before subscriptions can reference them | subscription requests |
| Glossary term | domain exists | glossary terms are hierarchical (parent-child); attaching a term to an asset applies its subscription policy | policy-driven governance |
| Subscription | published asset exists; consumer project exists | subscription requires APPROVAL before access is granted — NOT automatic by default | data access for consumer |
| Cross-account IAM role | source account exists; IAM role with trust policy for DataZone domain account | the trust policy must reference the DataZone domain account ID and the domain's execution role; missing trust = access denied | cross-account data reads |
| Environment blueprint | domain exists; blueprint enabled | blueprints are AWS-managed templates (data lake, data warehouse); they define the environment's default configuration | environment creation |
| Environment profile | domain exists; blueprint enabled; project exists | profiles map blueprint defaults to specific account/region deployment targets | environment provisioning |
| Metadata enrichment (Lambda) | project exists; data source exists | Lambda function runs on asset creation/update; auto-classifies and tags assets with glossary terms | automated governance |

**The cross-account IAM role row is the one a baseline model misses.**
DataZone operates in a hub-and-spoke model: the domain account is the
hub; data source accounts are spokes. The domain account's execution
role must be allowed to assume a role in each source account. Without
this trust chain, DataZone creates the data source but cannot read
any data — all crawl and read operations fail silently with Access
Denied. The procedure below forces an explicit IAM role check.

**Cross-dependency gotchas:**
- The IAM role in the source account must trust the DataZone domain
  account's execution role ARN, not just the account ID. The full
  role ARN is required in the trust policy.
- Subscriptions are per-asset, not per-project. Each asset (table,
  file, view) needs its own subscription request.
- Glossary term subscription policies are applied at subscription
  time, not retroactively. If you add a policy to a glossary term
  after subscriptions are approved, existing subscriptions are NOT
  re-evaluated.
- Environment profiles determine WHERE environments are deployed
  (which account and region). The blueprint determines WHAT is
  deployed (data lake vs data warehouse defaults).
- SSO federation is required for domain user management. DataZone
  does NOT support IAM users. All users must come through IAM
  Identity Center (SSO).



## Recent AWS features (2023-2026) (moved from SKILL.md)



**Recent AWS features (2023-2026):**

- **Auto-classification with SageMaker (2023-2024):** DataZone
  integrated SageMaker for ML-powered auto-classification of assets,
  detecting PII, data types, and column semantics without manual
  Lambda functions.

- **Cross-account subscription workflows (2024-2025):** Enhanced
  cross-account subscription support with automatic IAM role
  provisioning via CloudFormation stack deployment in the consumer
  account.

- **DataZone API GA (2024-2025):** The full DataZone API became
  generally available, enabling infrastructure-as-code (Terraform,
  CloudFormation) for domain, project, and data source management.

- **Glossary-driven policy engine (2024-2025):** Glossary terms can
  now carry complex subscription policies (multi-level approval,
  time-limited access, attribute-based access control).

- **Environment blueprint extensibility (2025-2026):** Custom
  blueprints beyond the default data lake and data warehouse, enabling
  domain-specific environment templates.

- **Metadata forms enhancement (2025-2026):** Structured metadata
  forms with validation rules, conditional fields, and automated
  enrichment via Lambda or SageMaker.

- **DataZone business-catalog (2025-2026):** Enhanced business
  catalog with searchable asset directory, data lineage, and impact
  analysis for governed data discovery at enterprise scale.


