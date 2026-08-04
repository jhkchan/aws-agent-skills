# End-to-end usage scenario: inspector2-coverage-finding-auditor

A walkthrough showing the skill auditing a multi-resource Inspector2 posture
that includes a coverage gap (SSM agent offline on a production instance), a
critical CVE confirmed internet-reachable, and a fully covered resource. This
exercises coverage-tier classification (Step 2), reachability amplification
(Step 4), finding-lifecycle filtering (Step 3), and account-level aggregation
(Step 7).

## Input (user prompt)

> Audit our Inspector2 posture in us-east-1 before our PCI compliance review
> next week. Here's the data from our account.

```text
Account: 123456789012
Region: us-east-1

Inspector2 account status (batch-get-account-status):
  EC2: ENABLED
  ECR: ENABLED
  LAMBDA: ENABLED
  LAMBDA_CODE: DISABLED

Resource inventory + coverage:
  - i-prod-web-01 (EC2, env=prod, critical=true)
    Coverage: lastScannedAt=2026-08-02, ACTIVE, SSM PingStatus=Online
  - i-prod-db-01 (EC2, env=prod, compliance=pci)
    Coverage: lastScannedAt=2026-06-10, SSM PingStatus=ConnectionLost
  - ecr-prod-api (ECR, env=prod)
    Coverage: lastScannedAt=2026-08-04, SUCCESSFUL, scanOnPush=true
  - lambda-report-gen (Lambda, env=prod)
    Coverage: lastScannedAt=2026-08-03, ACTIVE (standard scanning only)

Findings (status=OPEN):
  - i-prod-web-01:
      CVE-2021-44228 (log4j-core 2.14.1, CRITICAL, CVSS 10.0)
      NETWORK_REACHABILITY: port 443, ReachableFromInternet
  - i-prod-db-01:
      (no findings — SSM agent offline, no scan data)
  - ecr-prod-api:
      (none)
  - lambda-report-gen:
      CVE-2024-2222 (requests 2.27.1, MEDIUM, CVSS 5.4)

Note: CVE-2021-44228 is in the CISA KEV catalog.
Note: CVE-2024-2222 is NOT in the CISA KEV catalog.
```

## Skill output

```text
ACCOUNT: 123456789012 | REGION: us-east-1
VERDICT: CRITICAL
REASON: 1 of 4 resources CRITICAL. i-prod-web-01 has an OPEN CRITICAL CVE
(CVE-2021-44228, Log4Shell) confirmed internet-reachable via NETWORK_REACHABILITY
finding on port 443 (ReachableFromInternet). Reachability amplification confirms
an exploitable attack path — CVE is also in the CISA KEV catalog (active
exploitation). i-prod-db-01 is UNCOVERED (SSM PingStatus=ConnectionLost, PCI
compliance resource) — HIGH coverage gap. lambda-report-gen has PARTIAL coverage
(Lambda code scanning disabled) with a MEDIUM CVE. ecr-prod-api is COVERED.

RESOURCE SUMMARY:
  i-prod-web-01 (EC2)       — CRITICAL  [internet-reachable KEV critical CVE]
  i-prod-db-01 (EC2)        — HIGH      [SSM offline, PCI-compliance, stale scan]
  lambda-report-gen (Lambda)— MEDIUM   [partial coverage + medium CVE]
  ecr-prod-api (ECR)        — COVERED   [active scan, zero open findings]

REMEDIATION:
  1. i-prod-web-01: INCIDENT RESPONSE — contain FIRST by restricting the
     security group to deny inbound on port 443, then patch log4j-core to
     2.17.1+ via SSM Run Command (AWS-RunPatchBaseline). Verify finding
     transitions to SUPPRESSED within 24h.
  2. i-prod-db-01: re-enroll in SSM (verify IAM role has
     AmazonSSMManagedInstanceCore, check VPC endpoints for SSM connectivity).
     Once SSM is online, Inspector2 will auto-rescan.
  3. lambda-report-gen: enable Lambda code scanning for dependency-graph
     analysis. Patch requests to >= 2.32.0.
  4. ecr-prod-api: no action required. Monitor for coverage changes.
```

## What the skill caught that a generic assistant misses

1. **Reachability amplification.** A generic assistant flags CVE-2021-44228
   as "critical" but does not correlate the NETWORK_REACHABILITY finding to
   confirm the CVE is internet-exploitable on port 443. The skill's Step 4
   cross-references the vulnerable service port against reachability findings
   — confirming this is an active attack path, not just a high CVSS score.

2. **SSM-agent dependency for EC2 coverage.** A generic assistant may note
   that i-prod-db-01 has "no findings" and treat it as acceptable. The skill
   recognises that `SSM PingStatus=ConnectionLost` means the instance is
   UNCOVERED — Inspector2 cannot scan it. The absence of findings is
   meaningless because no scan ran. The skill classifies this as HIGH
   (PCI-compliance production resource with a coverage gap).

3. **Lambda partial coverage.** A generic assistant sees Lambda scanning is
   ENABLED and treats it as full coverage. The skill recognises that
   LAMBDA_CODE scanning is DISABLED — only the runtime is checked, not the
   function code or its dependencies. This is PARTIAL coverage, and the
   medium CVE in `requests` would not have been caught by standard scanning
   alone.

4. **Finding-lifecycle filtering.** The skill explicitly filters to
   status=OPEN findings and would have excluded SUPPRESSED findings (e.g.,
   if log4j had been patched in a prior image). A generic assistant may
   count all findings regardless of lifecycle state, inflating severity.

## Slash-command invocation

```
/aws:audit-inspector2-coverage-findings
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Inspector2 coverage and findings before the PCI review"
```

The orchestrator emits `[Phase: Audit | Skills routed:
inspector2-coverage-finding-auditor]` and hands off to this skill for the
VERDICT.

## Live-account follow-up (requires AWS CLI)

Gather the Inspector2 data for a live audit:

```bash
# Account-level enablement status
aws inspector2 batch-get-account-status --profile default

# Per-resource coverage
aws inspector2 list-coverage \
  --filter-criteria '{"accountId": [{"comparison": "EQUALS", "value": "123456789012"}]}' \
  --profile default

# Open findings
aws inspector2 list-findings \
  --filter-criteria '{"findingStatus": [{"comparison": "EQUALS", "value": "OPEN"}]}' \
  --profile default
```

For the internet-reachable CRITICAL finding, contain first:

```bash
# Contain: restrict the security group (immediate)
aws ec2 modify-security-group-rules \
  --group-id sg-prod-web-01 \
  --security-group-rules '[{"GroupId":"sg-prod-web-01","IpProtocol":"tcp","FromPort":443,"ToPort":443,"CidrIp":"0.0.0.0/0","Description":"TEMP BLOCK - revoke after patch"}]' \
  --profile default

# Patch: install log4j fix via SSM
aws ssm send-command \
  --document-name "AWS-RunPatchBaseline" \
  --instance-ids "i-prod-web-01" \
  --parameters '{"Operation":["Install"]}' \
  --profile default
```
