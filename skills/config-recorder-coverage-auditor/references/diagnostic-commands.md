# Diagnostic Commands (load on demand) — Config Recorder Coverage Auditor

Pre-flight and diagnostic command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight — multi-region sweep, pagination/throttling, live-account checks (moved from SKILL.md)

**Multi-region sweep note:** AWS Config is regional — each region has its
own recorder and delivery channel. An account-level audit must iterate all
enabled regions (`account:get-regions` or `aws ec2 describe-regions
--filters OptInStatus=opt-in-status --query 'Regions[].RegionName'`). A
common failure is auditing only us-east-1 and missing gaps in other regions.
For each region, run all six API calls. Use `--region <r>` on each.

**Pagination and throttling handling:** `describe-config-rules` and
`describe-conformance-packs` return paginated results. In accounts with
many rules or packs, a single API call returns only the first page —
silently undercounting rules and producing a false NO_RULES verdict.
Always paginate using `--next-token` / `NextToken` until the response
contains no `NextToken`, then aggregate the full rule/pack count before
classifying. Config API calls are also subject to throttling (rate limit
~10 req/s for read APIs in most regions). When auditing many regions
sequentially, expect intermittent `ThrottlingException` responses;
retry with exponential backoff (initial 200ms, factor 2, max 5 retries)
and treat a throttled response as "data missing — re-fetch," NOT as an
empty result that would produce a false NO_RULES or CONFIG_GAP verdict.

**Live-account pre-flight checks:**
1. Verify the caller's identity has these exact IAM permissions:
   `configservice:DescribeConfigurationRecorders`,
   `configservice:DescribeConfigurationRecorderStatus`,
   `configservice:DescribeDeliveryChannels`,
   `configservice:DescribeDeliveryChannelStatus`,
   `configservice:DescribeConfigRules`,
   `configservice:DescribeConformancePacks`,
   `configservice:DescribeOrganizationConformancePacks`,
   `configservice:DescribeConfigurationAggregators`.
   These are read-only auditor permissions and are separate from the
   service-linked role that Config itself uses.
2. Check `aws iam get-role --role-name AWSServiceRoleForConfig` — if this
   service-linked role is missing, the recorder cannot function regardless
   of its configuration. This is the most common root cause of
   `lastStatus: FAILURE`.
3. For multi-account audits, check whether an aggregator exists
   (`describe-configuration-aggregators`) — an aggregator collects data
   from source accounts but does NOT deploy recorders or rules. A region
   with only an aggregator and no local recorder has a CONFIG_GAP.

---

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-configuration-recorder`, `put-delivery-channel`, `start-configuration-
  recorder`, `stop-configuration-recorder`, `put-conformance-pack`,
  `delete-conformance-pack`), the auditor MUST emit:
  `CONFIRM: About to <action> in region <region> for account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Before changing the recorder configuration**, capture the current state:
  `aws configservice describe-configuration-recorders --region <r> --output json > /tmp/config-recorder-backup-$(date +%s).json`
  Recorder configuration changes are not versioned — there is no rollback
  without a backup.

- **Before starting a stopped recorder**, verify the `AWSServiceRoleForConfig`
  role exists and has the `AWSConfigRole` policy attached. Starting a
  recorder with a missing role immediately fails.

- **Before changing `allSupported` from false to true**, warn the operator
  about cost impact: `allSupported: true` records ALL resource types,
  including high-churn types (e.g., `AWS::CloudTrail::Trail` API events).
  In a large account, this can multiply Config costs by 5-10x.

- **Before deploying a conformance pack**, verify the region has not hit
  the 150-rule quota (`describe-config-rules --region <r>` and count). A
  conformance pack that pushes the region over quota silently fails to
  deploy rules.
