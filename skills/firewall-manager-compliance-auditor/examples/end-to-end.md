# End-to-end usage scenario: firewall-manager-compliance-auditor

A walkthrough showing the skill auditing a WAFV2 FMS policy that has both
live NONCOMPLIANT resources (Step 5) and a ResourceTags-only scope gap
(Step 3a), demonstrating verdict aggregation, the per-account drill-down
pattern, the detect-only mode finding, and the staged remediation
workflow (detect-first, then enforce).

## Input (user prompt)

> Audit this Firewall Manager policy before Monday's compliance review.
> We've been running it detect-only for a couple of months and I'm not
> sure what state we're in.

```yaml
Policy id: prod-edge-protect-multi-finding
PolicyName: prod-edge-waf-2026
PolicyType: WAFV2
PolicyState: READY
RemediationEnabled: false
DeleteUnusedFMSPolicies: false
ResourceTypeLists:
  - AwsWafv2WebAcl
  - AwsElasticLoadBalancingV2LoadBalancer
  - CloudFrontDistribution
ResourceTags:
  - Key: workload
    Value: customer-facing
IncludeMap:
  ORG_UNIT:
    - ou-abcd-11111111
    - ou-abcd-22222222
ExcludeMap: {}
```

Protection status (from `aws fms get-protection-status` and
`aws fms list-compliance-status`):

```yaml
ProtectedResourceCount: 42
NonCompliantResourceCount: 9
PerAccountViolators:
  "111111111111": 3   # prod-services OU
  "222222222222": 6   # prod-edge OU
ProtectedResourceCounters:
  - ResourceType: AwsWafv2WebAcl
    Count: 12
  - ResourceType: AwsElasticLoadBalancingV2LoadBalancer
    Count: 22
  - ResourceType: CloudFrontDistribution
    Count: 8
```

Context: AWS Config is enabled in every member account. The FMS admin
account is the security tooling account (delegated administrator).

## Skill output

```text
POLICY: prod-edge-protect-multi-finding
POLICY_NAME: prod-edge-waf-2026
POLICY_TYPE: WAFV2
VERDICT: NONCOMPLIANT
REASON: NonCompliantResourceCount=9 across two member accounts (Step 5)
— live violations on customer-facing WAF, ALB, and CloudFront resources.
RemediationEnabled is false (Step 4), compounding the exposure: FMS
detects but does not apply the WebACL, so the 9 violators are running
unprotected. ResourceTags=[workload=customer-facing] without an SCP
requirement on the tag (Step 3a) means any resource missing the tag is
silently out of scope.
FINDINGS:
  - [NONCOMPLIANT] 9 resources non-compliant across 2 accounts:
    222222222222 (6, prod-edge OU — dominates the violator count),
    111111111111 (3, prod-services OU) (Step 5)
  - [CONFIG_GAP] RemediationEnabled=false — policy is detect-only; FMS
    reports but does not apply the WebACL. The policy was created
    >60 days ago, indicating steady-state detect-only rather than
    onboarding staging (Step 4)
  - [INCOMPLETE_COVERAGE] ResourceTags-only scope on workload=
    customer-facing without an SCP enforcing the tag. Any ALB / WebACL
    / CloudFront distribution missing the tag is silently unprotected
    (Step 3a). ResourceTypeLists omits AwsApiGatewayStage — API Gateway
    stages are uncovered even when tagged (Step 3c)
  - [OK] PolicyState=READY, PolicyType=WAFV2 (current), FMS admin scope
    delegated, AWS Config enabled in every member account
REMEDIATION:
  1. Drill per-account: `aws fms get-compliance-detail --policy-id
     prod-edge-protect-multi-finding --member-account 222222222222`.
     Investigate why prod-edge OU dominates (6/9 violators) — likely a
     member-local WebACL override or an FMS service-linked role issue.
  2. Re-enable remediation AFTER the per-account drill-down: `aws fms
     put-policy --policy <json-with-RemediationEnabled-true>`. Capture
     current policy first: `aws fms get-policy --policy-id
     prod-edge-protect-multi-finding --output json > /tmp/fms-backup.json`.
     FMS policies are unversioned — there is no rollback without a backup.
  3. Stage the transition: keep RemediationEnabled=false for one final
     24-hour window after the WebACL is updated, then flip to true.
     Switching directly to enforce applies the WebACL to all 42
     resources simultaneously — a bad rule breaks every protected app.
  4. Add an SCP in the OU requiring `workload=customer-facing` on
     creation of WAF/ALB/CloudFront resources, OR broaden
     ResourceTypeLists and drop ResourceTags (use ResourceTags as
     refinement, not sole scope key).
  5. Add AwsApiGatewayStage to ResourceTypeLists to close the API
     Gateway coverage gap.
```

## Discussion

The scenario demonstrates three compounding failures that FMS operators
encounter in steady state:

1. **NONCOMPLIANT is the headline but not the root cause.** The 9
   violators are the visible symptom — the root cause is detect-only
   mode + ResourceTags-only scope. Re-enabling remediation alone would
   apply the WebACL to the 42 currently-tagged resources but leaves the
   silent untagged population unprotected.

2. **Per-account drill-down re-frames the response.** Account
   222222222222 (prod-edge OU) accounts for 6 of 9 violations. A uniform
   response ("re-enable remediation org-wide") would over-correct in
   accounts with 0-1 violations. The drill-down directs investigation
   to one OU's service-linked role or member-local override.

3. **ResourceTags without an SCP is advisory.** The tag-based scope
   silently excludes any resource without `workload=customer-facing`.
   Operators can remove the tag (intentionally or accidentally) to
   escape FMS scope. The defense is an SCP requiring the tag at resource
   creation — FMS itself cannot enforce tag presence.

## Related commands

- `/aws:audit-organizations-scp` — verify the SCP requiring
  `workload=customer-facing` on WAF/ALB/CloudFront resource creation.
- `/aws:audit-wafv2-web-acl` — audit the underlying WebACL referenced
  by `SecurityServicePolicyData.ManagedServiceData` for rule-level gaps.
- `/aws:audit-config-recorder-coverage` — confirm AWS Config coverage
  in every member account before trusting the NonCompliantResourceCount.
