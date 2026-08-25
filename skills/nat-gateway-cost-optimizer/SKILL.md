---
name: nat-gateway-cost-optimizer
description: Optimises NAT Gateway cost through traffic analysis, VPC endpoint design, and architecture selection. Identifies avoidable AWS-service traffic (S3, DynamoDB via FREE Gateway endpoints; ECR, SSM, STS, Secrets Manager, CloudWatch, KMS via Interface endpoints), runs break-even maths on interface endpoints (~160 GB/month threshold at $0.045/GB NAT vs $0.01/GB endpoint), selects single vs multi-AZ NAT topology by environment, evaluates NAT Instance alternatives for dev/test, and emits a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per VPC with the exact endpoint-creation payload and estimated monthly savings. Use when reviewing NAT Gateway spend, triaging unexpected data-processing charges, planning a FinOps VPC endpoint rollout, or deciding between NAT Gateway and NAT Instance for a non-HA workload.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline configuration classification works from pasted VPC topology, Cost Explorer data, and VPC Flow Logs summaries. Live-account optimisation uses aws ec2 describe-nat-gateways, aws ec2 describe-vpc-endpoints, aws ce get-cost-and-usage with filter for NatGateway usage type, aws ec2 describe-route-tables, and aws logs start-query for VPC Flow Logs traffic breakdown (AWS CLI v2, SSO or key-based credentials)...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing NAT Gateway spend, triaging unexpected AWS data-processing charges, designing a VPC endpoint rollout, deciding between single vs multi-AZ NAT topology, evaluating NAT Instance for dev/test, or building a networking FinOps plan.
  when_not_to_use: Auditing Transit Gateway routing (use the networking auditor), VPC peering topology design (architectural, not cost-driven), Direct Connect procurement, or Security Group rule review. This skill focuses on NAT Gateway cost reduction via VPC endpoints and topology choice, not on connectivity troubleshooting or route-table correctness audits.
  activation_triggers: optimise NAT Gateway cost, NAT Gateway data processing charge, VPC endpoint cost benefit, S3 traffic through NAT, create Gateway VPC Endpoint, single NAT Gateway vs multi-AZ, NAT Instance alternative, reduce NAT Gateway bill, VPC Flow Logs traffic breakdown, FinOps networking review, PrivateLink endpoint savings, ECR traffic through NAT, DynamoDB VPC endpoint, unexpected AWS data transfer charge
  invocation_schema: 'Input: either (a) a VPC configuration (NAT Gateways, route tables, VPC endpoints, subnet-to-AZ mapping, monthly data-processing GB from Cost Explorer), OR (b) a VPC ID for live-account optimisation. Output: a deterministic VPC/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION block per VPC, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline classification):\nVPC: vpc-0abc123\nRegion: us-east-1\nEnvironment: production\nNAT Gateways: 3 (one per AZ — us-east-1a, 1b, 1c)\nData processing (last 30 days, Cost Explorer): 2,400 GB total\nCurrent VPC Endpoints: none\nTraffic breakdown (VPC Flow Logs, last 7 days):\n  - S3: 900 GB/month\n  - DynamoDB: 200 GB/month\n  - ECR: 150 GB/month\n  - Other AWS services: 150 GB/month\n  - Internet (non-AWS): 1,000 GB/month\nEmit the standard optimization block (VPC, VERDICT, REASON,\nRECOMMENDATION, SAVINGS, IMPLEMENTATION)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: NAT Gateway, VPC Endpoint, Gateway Endpoint, Interface Endpoint, PrivateLink, S3 Gateway Endpoint, DynamoDB Gateway Endpoint, ECR endpoint, SSM endpoint, STS endpoint, Secrets Manager endpoint, data processing charge, cost optimization, FinOps, NAT Instance, cross-AZ data transfer, VPC Flow Logs, Cost Explorer, AWS PrivateLink
  tags: nat-gateway, vpc, networking, cost-optimization, finops, vpc-endpoint, privatelink
---

# NAT Gateway Cost Optimizer

## What this skill does

Translates NAT Gateway spend into a concrete VPC endpoint rollout plan and
a dollar-denominated savings estimate. NAT Gateway is the #1 source of
unexpected AWS bills: every GB processed costs $0.045, and the most common
sources of that traffic (S3, DynamoDB) can be redirected to **free** Gateway
VPC Endpoints. The verdict is the **highest-leverage action** across four
dimensions — Gateway endpoints (free), Interface endpoints (break-even
analysis), NAT topology (single vs multi-AZ), and NAT Instance substitution
(dev/test) — applied in priority order. Always pairs the recommendation with
the exact `create-vpc-endpoint` payload so the operator can paste, review,
and apply.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving endpoint or topology change available | Emit recommended endpoints/topology + savings estimate |
| `OPTIMIZED` | An endpoint or topology change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | All applicable Gateway endpoints exist, Interface endpoints above break-even are in place, topology matches environment | No action — confirm posture |

**Priority order for opportunity dimensions (apply in this sequence, aggregate
all that apply into a single recommendation):**

1. **Gateway endpoints for S3 and DynamoDB** — FREE, always create them if
   any S3/DynamoDB traffic flows through NAT. This is the single largest
   quick win on most AWS accounts.
2. **Interface endpoints for high-traffic AWS services** (ECR, SSM, STS,
   Secrets Manager, CloudWatch, KMS) — apply break-even maths; recommend if
   monthly traffic > ~160 GB.
3. **NAT topology** — single NAT Gateway for non-prod (saves base hourly
   cost), one per AZ for prod (avoids cross-AZ transfer).
4. **NAT Instance substitution** — dev/test workloads where HA is not
   required; fixed EC2 cost instead of per-GB processing.

> Pricing detail moved to [references/vpc-endpoint-pricing-matrix.md](references/vpc-endpoint-pricing-matrix.md): full us-east-1 cost-baseline table.
> Load on demand when break-even maths needs component rates; the rule of thumb below stays authoritative.

**Break-even rule of thumb:** for an Interface endpoint, monthly savings =
`(GB × $0.045) − (GB × $0.01 + $7.30 × num_AZs)`. The break-even point is
~**160 GB/month per AZ** of traffic to the target service.

## Mindset and philosophy

**One-line takeaway:** Gateway endpoints (S3, DynamoDB) are free and should
exist on every VPC that has a NAT Gateway — their absence is a defect, not
an optimisation opportunity. Four networking realities drive the verdict:

> The four networking realities behind this mindset are expanded in [references/expert-knowledge.md](references/expert-knowledge.md).
> Load on demand for the full treatment of each reality before issuing a verdict.

## Pre-flight: VPC metadata gate

> Full pre-flight command listing (NAT enumeration, endpoints, Cost Explorer, Flow Logs, route tables, data-quality short-circuits) moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Run every check there before classification — misclassifying these produces false positives.

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious NAT Gateway and VPC endpoint behaviours

> Step-0 expert-knowledge summary moved to [references/expert-knowledge.md](references/expert-knowledge.md) (non-obvious NAT Gateway and VPC endpoint behaviours).
> Load on demand; each behaviour changes a recommendation if ignored.

### Step 1: Gateway endpoints for S3 and DynamoDB (FREE — always create)

If ANY S3 or DynamoDB traffic flows through the NAT Gateway and the
corresponding Gateway endpoint does not exist:

**Pattern — S3 Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids <rtb-id-1> <rtb-id-2> \
  --output json
```

**Pattern — DynamoDB Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids <rtb-id-1> <rtb-id-2> \
  --output json
```

**Savings estimate:**
```
S3 savings   = S3_GB_through_NAT × $0.045
DynamoDB savings = DDB_GB_through_NAT × $0.045
```

These savings are captured in FULL — Gateway endpoints are free, so every
dollar of redirected traffic is a dollar saved. There is no break-even
threshold.

If S3 or DynamoDB traffic exists and the Gateway endpoint is absent:
**OPPORTUNITY_FOUND** on this dimension. This is the single highest-leverage
recommendation the skill can make.

### Step 2: Interface endpoints for high-traffic AWS services (break-even analysis)

For each AWS service with significant traffic through NAT (ECR, SSM, STS,
Secrets Manager, CloudWatch, KMS, CodeArtifact, etc.), compute the break-even:

```
Monthly savings = (service_GB × $0.045) − (service_GB × $0.01 + $7.30 × num_AZs)
```

**Decision matrix:**

| Monthly traffic to service | Verdict | Recommendation |
|---|---|---|
| > 200 GB/month (> break-even) | **OPPORTUNITY_FOUND** | Create Interface endpoint in the AZs that originate the traffic |
| 100-200 GB/month (near break-even) | **OPPORTUNITY_FOUND** (MEDIUM confidence) | Create Interface endpoint in 1-2 AZs; monitor for 30 days |
| < 100 GB/month (< break-even) | Skip (ALREADY_OPTIMAL for this service) | Do NOT create — endpoint would increase cost |

**Pattern — ECR Interface Endpoint (most common high-traffic candidate):**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --subnet-ids <subnet-1a> <subnet-1b> \
  --security-group-ids <sg-id> \
  --private-dns-enabled \
  --output json

# Also create the ecr.dkr endpoint for Docker pull/push (separate service name)
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.dkr \
  --subnet-ids <subnet-1a> <subnet-1b> \
  --security-group-ids <sg-id> \
  --private-dns-enabled \
  --output json
```

**Common Interface endpoint candidates and their typical break-even:**

| Service | Service name suffix | Typical traffic pattern | Break-even GB/month (per AZ) |
|---|---|---|---|
| ECR (api + dkr) | ecr.api, ecr.dkr | Container image pulls/pushes | ~160 GB (note: TWO endpoints needed) |
| SSM | ssm | Systems Manager agent check-ins | Low (usually skip) |
| STS | sts | AssumeRole calls | Very low (skip) |
| Secrets Manager | secretsmanager | App secret fetches | Low unless high-frequency rotation |
| CloudWatch Logs | logs | Application log shipping | High if logs are verbose; evaluate |
| KMS | kms | Encrypt/decrypt API calls | Low (skip) |
| CodeArtifact | codeartifact.api | Package pulls | Medium; evaluate by CI volume |

### Step 3: NAT topology optimisation (single vs multi-AZ)

The topology decision depends on the environment AND the cross-AZ traffic
volume.

**Decision matrix:**

| Environment | Cross-AZ traffic volume | Recommendation |
|---|---|---|
| Production, high throughput (> 500 GB/month cross-AZ) | High | Keep one NAT Gateway per AZ — cross-AZ transfer would exceed the base-cost saving |
| Production, low throughput (< 100 GB/month cross-AZ) | Low | Consolidate to a single NAT Gateway — base-cost saving exceeds cross-AZ transfer |
| Non-production (dev/test/staging) | Any | Single NAT Gateway — accept cross-AZ cost; HA is not required |
| Non-production, minimal outbound (< 10 GB/month) | Very low | Consider NAT Instance (Step 4) instead |

**Cross-AZ cost calculation for single-NAT topology:**
```
Cross-AZ cost = total_GB_from_other_AZs × $0.02  (both directions)
Base saving = (eliminated_gateways × $32.85)
Net = base_saving − cross_AZ_cost
```

If `Net > 0`, single-NAT is cheaper. If `Net < 0`, keep multi-NAT.

**Pattern — consolidate to single NAT Gateway (non-prod):**
1. Update route tables in all private subnets to point `0.0.0.0/0` to the
   single remaining NAT Gateway.
2. Delete the redundant NAT Gateways:
   `aws ec2 delete-nat-gateway --nat-gateway-id <id>`.
3. Release the Elastic IPs:
   `aws ec2 release-address --allocation-id <eip-alloc-id>`.

### Step 4: NAT Instance substitution (dev/test only)

For dev/test environments with minimal outbound traffic and no HA requirement:

**Pattern — NAT Instance (t3.micro, dev/test):**
```bash
# Launch a NAT Instance from the public AMI (search for the latest amzn-ami-vpc-nat AMI)
aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/amzn-ami-vpc-nat-hvm \
  --instance-type t3.micro \
  --subnet-id <public-subnet> \
  --associate-public-ip-address \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=nat-instance-dev}]" \
  --output json

# Disable source/destination checks (required for NAT function)
aws ec2 modify-instance-attribute --instance-id <id> --no-source-dest-check

# Update route tables to point to the instance instead of the NAT Gateway
aws ec2 replace-route --route-table-id <rtb-id> \
  --destination-cidr-block 0.0.0.0/0 --instance-id <id>
```

**Savings estimate:**
```
NAT Gateway cost = $32.85 (base) + (GB × $0.045)
NAT Instance cost = $8.47 (t3.micro, flat) + (GB × $0)  [no per-GB charge]
Saving = NAT_Gateway_cost − $8.47
```

**Reliability warning (MUST surface in output):**
- NAT Instance is a single point of failure — no SLA, no automatic failover.
- Bandwidth is capped by instance type (~1 Gbps for t3.micro).
- If the underlying host fails, outbound traffic stops until the instance is
  replaced (manual or via Auto Scaling recovery, which adds 2-5 minutes of
  downtime).
- NOT suitable for production workloads.

### Step 5: Aggregation — emit the highest-leverage recommendation

Aggregate ALL applicable dimensions into a single recommendation. The verdict
is `OPPORTUNITY_FOUND` if any dimension has a saving. The recommendation
includes the full endpoint-creation and topology-change plan.

If no dimension has an opportunity (all applicable Gateway endpoints exist,
Interface endpoints are above break-even where justified, topology matches
environment): **ALREADY_OPTIMAL**.

If the recommendation was applied this session and verified: **OPTIMIZED**.

## Output format (per VPC)

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION:
  <list of endpoint-creation and topology-change actions>
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <Interface endpoint break-even assumptions, NAT Instance reliability warnings>
IMPLEMENTATION:
  1. <create-vpc-endpoint CLI command>
  2. <delete-nat-gateway CLI command>
  3. <verification command>
```

### Worked examples (see references/worked-examples.md)

> Secondary worked examples moved to [references/worked-examples.md](references/worked-examples.md) — three full end-to-end scenarios.
> Load on demand; the primary example under the STRICT output contract below stays in this file.

## STRICT output contract

The rules below are hard constraints. Violating any one produces an
arithmetic contradiction or a misclassification that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block per VPC using these literal
labels, in this order. Do NOT substitute markdown headings, camelCase,
or bold variants.

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION:
  <list of endpoint-creation and topology-change actions>
SAVINGS:
  CURRENT_MONTHLY: $<amount>    ← MUST show base + data-processing subtotals
  PROJECTED_MONTHLY: $<amount>
  MONTHLY_SAVING: $<amount>     ← MUST equal CURRENT − PROJECTED, 2 decimals
  ANNUAL_SAVING: $<amount>      ← MUST equal MONTHLY × 12
  CAVEATS: <break-even assumptions, reliability warnings>
IMPLEMENTATION:
  1. <create-vpc-endpoint / delete-nat-gateway / replace-route CLI command>
  2. <verification command>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: OPPORTUNITY_FOUND` with
   `MONTHLY_SAVING: $0.00`.** If every dimension nets zero saving, the
   verdict MUST be `ALREADY_OPTIMAL`. An `OPPORTUNITY_FOUND` block with
   a zero savings line is a direct contradiction.

2. **NEVER show a savings figure where `CURRENT_MONTHLY −
   PROJECTED_MONTHLY` does not equal `MONTHLY_SAVING`.** Round both
   sides to 2 decimal places. If they differ, fix the arithmetic before
   emitting — do NOT append an "Adjusted to Cost Explorer baseline" or
   "rounding" reconciliation that masks the mismatch.

3. **NEVER recommend an Interface endpoint without citing the GB/month
   traffic volume AND the break-even threshold (~160 GB/month per AZ).**
   The RECOMMENDATION line MUST state: `<service>: <X> GB/month vs
   <break-even> GB/month break-even for <N>-AZ`. An Interface endpoint
   on traffic below break-even INCREASES cost — that is a negative
   saving and MUST NOT appear as `OPPORTUNITY_FOUND`.

4. **NEVER include Gateway endpoint (S3, DynamoDB) costs on the cost
   side of the SAVINGS equation.** Gateway endpoints are free — $0
   hourly, $0 per-GB. Their absence from a VPC with S3/DynamoDB NAT
   traffic is always `OPPORTUNITY_FOUND` with the full redirected-GB
   dollar amount captured as saving.

5. **NEVER recommend a NAT Instance without the reliability warning in
   CAVEATS.** The warning MUST include: "single point of failure, no
   SLA, not suitable for production." A NAT Instance recommendation
   without this caveat is non-compliant.

6. **NEVER emit a "NOTE: discrepancy due to partial-month data" or
   "Adjusted to Cost Explorer baseline ratio" line that reconciles
   arithmetic errors.** If Cost Explorer shows a different figure than
   the computed subtotal, use the Cost Explorer figure as
   `CURRENT_MONTHLY` and recompute `PROJECTED_MONTHLY` from it
   proportionally. The two MUST reconcile without a narrative patch.

7. **NEVER recommend deleting a NAT Gateway without pairing the
   deletion with `aws ec2 release-address` for the associated EIP.**
   An unreleased EIP incurs $3.65/month indefinitely — the
   IMPLEMENTATION block MUST include the release-address step.

8. **NEVER aggregate traffic across services to hit a single Interface
   endpoint break-even.** Each Interface endpoint is a separate
   financial decision with its own break-even. S3 (100 GB) + ECR (60
   GB) does NOT justify an ECR endpoint at 160 GB.

### Perfect example output — OPPORTUNITY_FOUND with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
VPC: vpc-0abc123
VERDICT: OPPORTUNITY_FOUND
REASON: 3-AZ production VPC with 3 NAT Gateways processing 2,400 GB/month.
  No Gateway endpoints exist — 900 GB/month S3 + 200 GB/month DynamoDB
  flow through NAT (Step 1). ECR at 150 GB/month is below 160 GB/AZ
  break-even (Step 2, skipped). Topology correct for production (Step 3).
RECOMMENDATION:
  1. Create S3 Gateway Endpoint (FREE) — reroutes 900 GB/month off NAT.
  2. Create DynamoDB Gateway Endpoint (FREE) — reroutes 200 GB/month.
  3. Skip ECR Interface Endpoint: 150 GB < 160 GB break-even for 1-AZ.
  4. Topology: keep 3 NAT Gateways (production, high throughput).
SAVINGS:
  CURRENT_MONTHLY: $206.55
    NAT base: 3 × $32.85 = $98.55
    NAT data processing: 2,400 GB × $0.045 = $108.00
  PROJECTED_MONTHLY: $157.05
    NAT base: 3 × $32.85 = $98.55 (unchanged)
    NAT data processing: 1,300 GB × $0.045 = $58.50
    Gateway endpoints: $0.00 (free)
  MONTHLY_SAVING: $49.50
    ($206.55 − $157.05 = $49.50 ✓)
    (1,100 GB × $0.045 = $49.50 ✓)
  ANNUAL_SAVING: $594.00
  CAVEATS:
    - Gateway endpoints are free — savings captured in full.
    - ECR Interface endpoint NOT recommended: below break-even.
    - Cross-region S3 access not covered by regional Gateway endpoint.
IMPLEMENTATION:
  1. CONFIRM: Create S3 + DynamoDB Gateway endpoints on vpc-0abc123. Proceed?
  2. aws ec2 create-vpc-endpoint --vpc-id vpc-0abc123 --service-name com.amazonaws.us-east-1.s3 --vpc-endpoint-type Gateway --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  3. aws ec2 create-vpc-endpoint --vpc-id vpc-0abc123 --service-name com.amazonaws.us-east-1.dynamodb --vpc-endpoint-type Gateway --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  4. Verify: aws ec2 describe-vpc-endpoints --filter "Name=vpc-id,Values=vpc-0abc123"
  5. After 24h, re-query Cost Explorer — expect ~$49.50/mo reduction.
```

**Self-check before emit:**
- [ ] `CURRENT_MONTHLY − PROJECTED_MONTHLY == MONTHLY_SAVING` (2 decimals)?
- [ ] `MONTHLY_SAVING × 12 == ANNUAL_SAVING`?
- [ ] Every Interface endpoint recommendation cites GB/month vs break-even?
- [ ] NAT Instance recommendation includes reliability warning?
- [ ] NAT Gateway deletion paired with `release-address`?
- [ ] No "adjusted" or "discrepancy" reconciliation lines?

## Verdict consistency rules (prevent misclassification)

The skill MUST emit verdicts that are mathematically and logically
self-consistent:

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every dimension,
   the verdict MUST be `ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND`.

2. **Negative-savings rule.** If an Interface endpoint would cost MORE than
   the NAT processing it replaces (traffic below break-even), do NOT recommend
   it. The verdict for that dimension is "no action." Emitting
   `OPPORTUNITY_FOUND` with a negative saving is a hard error.

3. **OPPORTUNITY_FOUND requires a non-zero savings line.** When emitting
   `OPPORTUNITY_FOUND`, the SAVINGS block must show a positive `MONTHLY_SAVING`
   for at least one dimension.

4. **SAVINGS arithmetic check.** `CURRENT_MONTHLY − PROJECTED_MONTHLY` MUST
   equal `MONTHLY_SAVING`. Round to 2 decimal places.

5. **Gateway endpoint is always free.** Never include a Gateway endpoint
   (S3, DynamoDB) in the cost side of the equation. Its absence from a VPC
   with S3/DynamoDB traffic is always OPPORTUNITY_FOUND.

6. **NAT Instance recommendations MUST include the reliability warning.**
   A NAT Instance recommendation without the "single point of failure,
   not suitable for production" caveat is non-compliant.

7. **Elastic IP release must accompany NAT Gateway deletion.** A NAT Gateway
   deletion without `release-address` for the associated EIP leaves a
   $3.65/month orphan charge.

## Error handling and edge cases (see references/troubleshooting.md)

> Error-handling deep dives, API error tables, and edge-case topologies moved to [references/troubleshooting.md](references/troubleshooting.md).
> Load on demand when a CLI/data-source call fails or the topology is unusual.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend an Interface endpoint without quantifying monthly
   traffic volume.** An Interface endpoint on a low-traffic VPC INCREASES
   cost by $7.30/AZ/month. Always cite GB/month and confirm it exceeds
   break-even (~160 GB/month per AZ).

2. **NEVER recommend a NAT Instance for production.** NAT Instance is a
   single point of failure with no SLA and bandwidth caps. Dev/test only.
   A cost saving that causes a production outage is a net loss.

3. **NEVER delete a NAT Gateway without updating route tables FIRST and
   pairing deletion with `release-address` for the EIP.** A route still
   pointing to a deleted gateway black-holes the subnet; an unreleased
   EIP leaks $3.65/month indefinitely.

4. **NEVER recommend single-NAT topology for production with high
   cross-AZ traffic without computing cross-AZ transfer cost.** The
   cross-AZ charge ($0.01/GB each direction) can exceed the base-cost
   saving of eliminating gateways.

5. **NEVER auto-apply endpoint or topology changes without the CONFIRM
   gate, and NEVER batch VPC changes.** A wrong route-table update can
   black-hole an entire VPC's outbound traffic; process one VPC per
   CONFIRM gate so errors do not cascade.

Additional NEVER rules (aggregate break-even, cross-region Gateway
coverage, S3 Interface vs Gateway, Flow Logs filtering, NAT Instance
source/dest-check) appear in `references/expert-knowledge.md` and the
FORBIDDEN output patterns section above.

## Pre-flight safety checks (run before any remediation CLI)

> Pre-flight safety check listing (CONFIRM gate, route-table backup, state verification, policy review) moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
> Run before any remediation CLI.

## Recent AWS features (2024-2026)

> Recent AWS features (2024-2026) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
> Load on demand for newer capabilities that affect endpoint topology and sizing choices.

## Domain

AWS CloudOps / Networking Cost Optimisation & VPC Endpoint Design.

## AWS documentation

- **Amazon VPC User Guide — VPC Endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **AWS PrivateLink** — https://aws.amazon.com/privatelink/
- **NAT Gateways** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- **Gateway VPC Endpoints (S3, DynamoDB)** — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- **Interface VPC Endpoints (PrivateLink)** — https://docs.aws.amazon.com/vpc/latest/privatelink/interface-endpoints.html
- **VPC Pricing — NAT Gateway** — https://aws.amazon.com/vpc/pricing/
- **AWS CLI Command Reference: ec2** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight VPC metadata gate commands and pre-flight safety checks.
- [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2024-2026).
- [references/expert-knowledge.md](references/expert-knowledge.md) — Step-0 non-obvious behaviours and the four networking realities.
- [references/troubleshooting.md](references/troubleshooting.md) — error handling, API error tables, edge cases.
- [references/worked-examples.md](references/worked-examples.md) — three full end-to-end worked examples.
- [references/vpc-endpoint-pricing-matrix.md](references/vpc-endpoint-pricing-matrix.md) — detailed pricing matrix and cost baseline.

