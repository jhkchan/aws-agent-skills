# Diagnostic Commands — Firewall Manager Compliance Auditor

Pre-flight and diagnostic command listings plus per-verdict remediation runbooks, moved verbatim from SKILL.md. Load on demand.

## Live-account pre-flight checks (from § Pre-flight)
**Live-account pre-flight checks (skip if doing offline policy-doc
audit):**
1. Verify the caller's identity is the FMS administrator account
   (`aws fms get-admin-scope`). Member accounts can READ policies via
   `aws fms list-policies` but CANNOT remediate. Remediation commands
   emitted from a member account fail with `AccessDeniedException`.
2. Verify the AWS Organization is present and the FMS admin is a
   delegated administrator (`aws organizations
   list-delegated-administrators --service-principal
   fms.amazonaws.com`). FMS without Organizations is a hard
   misconfiguration — the service has no scope.
3. Verify AWS Config is enabled in EVERY member account and region in
   scope. FMS uses Config as its compliance data source — without Config,
   a member account is a dark spot: `NonCompliantResourceCount` reads as
   0 (no data), not "compliant." Run `aws configservice
   describe-configuration-recorders` per member per region before
   trusting the count.
4. Verify the FMS notification channel
   (`aws fms get-notification-channel`). Without SNS topic wiring,
   NONCOMPLIANT transitions produce zero operator alerting — the gap
   surfaces only when a Console operator happens to look.

## Pre-flight safety checks (run before any remediation CLI)
- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-policy`, `delete-policy`, `associate-admin-account`), emit:
  `CONFIRM: About to <action> on policy <id> in account <admin-acct>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. FMS
  policy changes propagate to ALL member accounts in scope — there is
  no staged rollout.
- **MANDATORY QUOTA PRE-CHECK before `put-policy` creating a new
  policy.** Run `aws fms list-policies --output json | jq '.PolicyList
  | length'`. If the count is at or above 50 (the org soft cap),
  REFUSE to emit the create command and instruct the operator to
  delete unused policies first. Hitting the cap mid-remediation leaves
  the org in a partially-migrated state — `LimitExceededException` on
  `put-policy` is not recoverable without a deletion.
- **Admin scope verification.** Confirm the caller is the FMS
  administrator: `aws fms get-admin-scope --profile <p>`. Member
  accounts CANNOT remediate — `put-policy` fails with
  `AccessDeniedException`. Surface this BEFORE the operator approves.
- **Capture current policy for rollback.**
  `aws fms get-policy --policy-id <id> --output json > /tmp/<id>-backup-$(date +%s).json`
  BEFORE any modification. FMS policies are not versioned — `put-policy`
  replaces the entire policy atomically. There is no undo without a
  backup.
- **Verify ProtectedResourceCount before deletion.**
  `aws fms get-protection-status --policy-id <id>`. If the count is >0,
  deleting the policy removes protection from those resources
  immediately. Require explicit operator acknowledgement of the count.
- **Verify the WebACL exists before WAFV2 policy creation.** The
  WebACL referenced in `SecurityServicePolicyData.ManagedServiceData`
  must exist in the policy's region. A `put-policy` with a non-existent
  WebACL is accepted but the policy enters NOT_READY.
- **Detect-only staging for new policies.** Any new FMS policy should
  be created with `RemediationEnabled: false` for the first 1-2 weeks.
  Transition to `true` only after reviewing `list-compliance-status`
  output. Switching directly to enforce applies the WebACL/SG to all
  resources simultaneously — false positives break applications.
- **Prefer WebACL edits over FMS policy swaps.** When the rule set
  needs updating, edit the WebACL via `wafv2 update-web-acl` (staged,
  reversible) and let FMS re-apply. Swapping the WebACL via a new FMS
  policy is atomic — a bad WebACL breaks every protected resource at
  once.
- **Multi-region awareness.** For multi-region workloads, a remediation
  must be applied to each regional FMS policy independently. FMS does
  NOT sync policies across regions.
- **For NONCOMPLIANT findings**, treat as incident-response if
  RemediationEnabled was previously false — the violations represent
  resources that were silently unprotected during the detect-only
  window. Audit CloudTrail for relevant API activity during the gap.

## Remediation guidance
**Remediation ordering principle:** always prefer the smallest blast-
radius change first. Edit the WebACL/SG (one resource type, reversible)
BEFORE editing the FMS policy (atomic across all resources). Stage any
new FMS policy in detect-only mode before enforcing.

### For NONCOMPLIANT — live violations (Step 5)

1. Drill per-member-account:
   `aws fms get-compliance-detail --policy-id <id> --member-account <acct>`
   to enumerate violators.
2. If RemediationEnabled is true, the violations indicate Config
   discovered resources that FMS could not bring into compliance
   (typically: underlying WebACL missing, member-local override, or
   resource deletion race). Address root cause per violator.
3. If RemediationEnabled is false, re-enable after staging:
   `aws fms put-policy --policy <json-with-RemediationEnabled-true>`.
4. For SHIELD_ADVANCED policies, verify each violator resource still
   exists — Shield protection on a deleted resource is a stale finding.
5. For NETWORK_FIREWALL policies, provision the missing firewall in
   the violating VPC: `aws network-firewall create-firewall`. FMS will
   manage the policy once the firewall exists.

### For INCOMPLETE_COVERAGE — scope gaps (Step 3)

1. For ResourceTags-only scope: either add the tag to all resources
   that should be in scope (enforced via SCP), or broaden
   ResourceTypeLists and use ResourceTags as a refinement.
2. For missing critical resource types: update ResourceTypeLists via
   `aws fms put-policy` with the additional types. Verify the change
   does not exceed the 50-policy org quota.
3. For missing OUs in IncludeMap: cross-reference `aws organizations
   list-roots` and add the missing OU IDs. Stale OU IDs in IncludeMap
   must be removed — they are silently ignored today but may produce
   errors on future FMS versions.
4. After scope expansion, re-evaluate in detect-only mode
   (`RemediationEnabled: false`) for 1-2 weeks before re-enforcing.

### For CONFIG_GAP — policy misconfiguration

1. **PolicyState NOT_READY**: investigate root cause. Run
   `aws fms get-policy --policy-id <id>` and inspect
   `PolicyUpdateToken`. If the underlying WebACL/SG baseline is
   missing, recreate it. If stuck for >24h, open an AWS support case.
2. **RemediationEnabled false**: stage transition to true. Review
   `list-compliance-status` first; address any existing violations
   before flipping to enforce.
3. **PolicyType WAF (legacy)**: create a parallel WAFV2 policy with
   equivalent WebACL coverage. Verify parity via
   `get-protection-status` comparison. Then
   `aws fms delete-policy --policy-id <legacy>`.
4. **Empty ResourceTypeLists**: identify the intended scope and add
   types. If the policy is genuinely unused (>90 days, 0 protected),
   delete it.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying FMS notification channel is wired
   (`aws fms get-notification-channel`) — operators miss NONCOMPLIANT
   transitions without SNS alerts.
3. Recommend periodic re-audit (quarterly) — FMS scope drifts as
   accounts join/leave the Org and resources are created/destroyed.
4. For Shield Advanced policies, recommend annual review of protected
   resource coverage against current infra (EIPs, LBs, CloudFront).

## Practical execution reference — pagination and multi-region iteration
These patterns are the execution layer the classification logic above
depends on. Skipping them produces silent under-counts and false OK
verdicts.

### Pagination — drain every NextToken

Every FMS list API is paginated. Truncating after the first page silently
undercounts scope and compliance:

| API | Max per page | Required loop |
|---|---|---|
| `aws fms list-policies` | 100 (default 100) | Drain `NextToken` to completion; audit every returned policy. |
| `aws fms list-compliance-status --policy-id <id>` | 100 | Page per policy until `NextToken` is empty; aggregate `PolicyComplianceStatus` across all member accounts. |
| `aws fms list-member-accounts` | 100 | Page to enumerate the full in-scope member set; cross-reference against the Organization tree. |
| `aws fms get-protection-status --policy-id <id>` | single response | `ProtectedResourceCounters` is a complete list — no pagination, but verify it is non-empty. |

Pattern (bash, all AWS CLI v2):

```bash
TOKEN=""
while :; do
  if [ -z "$TOKEN" ]; then
    RESP=$(aws fms list-compliance-status --policy-id "$PID" --output json)
  else
    RESP=$(aws fms list-compliance-status --policy-id "$PID" --next-token "$TOKEN" --output json)
  fi
  echo "$RESP" | jq -r '.PolicyComplianceStatusList[]'
  TOKEN=$(echo "$RESP" | jq -r '.NextToken // empty')
  [ -z "$TOKEN" ] && break
done
```

**Stale pagination caveat:** AWS Config-backed resource inventories lag
by 5-15 minutes. A `list-compliance-status` response reflects the
Config snapshot, not real-time. A resource created 2 minutes ago is NOT
in the compliance count yet. Note this in the audit timestamp.

### Multi-region iteration

WAF, SG, and Network Firewall policies are regional. Auditing a single
region misses the other N-1 regional policies. The iteration:

```bash
for REGION in $(aws account list-regions --profile "$P" --output json \
  | jq -r '.Regions[] | select(.RegionOptStatus!="DISABLED") | .RegionName'); do
  aws fms list-policies --region "$REGION" --profile "$P" --output json \
    | jq -r '.PolicyList[].PolicyId'
done
```

- **Skip DISABLED regions** — FMS cannot operate there even if a policy
  exists (it will be stale).
- **Shield Advanced CloudFront policies are global** — they appear in
  every region's `list-policies`. De-duplicate by `PolicyId` to avoid
  double-counting.
- **`list-policies` returns policies MANAGED BY the calling admin
  account.** With per-OU admin delegation (2024+), each admin sees only
  its scope. Iterate `aws fms list-admin-accounts-for-organization` and
  assume each admin role to enumerate the full policy set.

