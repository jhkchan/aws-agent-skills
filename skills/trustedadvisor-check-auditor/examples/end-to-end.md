# End-to-end usage scenario: trustedadvisor-check-auditor

A walkthrough showing the skill auditing a Trusted Advisor check result
that has a security error (open RDP port 3389 to 0.0.0.0/0) plus stale
result timestamps, demonstrating severity aggregation, the category-severity
matrix (Security error = CRITICAL_CHECK vs Cost error = WARNING_CHECK), the
staleness dimension, and the support-tier gate.

## Input (user prompt)

> Review these Trusted Advisor check results from our production account
> before the upcoming compliance audit. I grabbed the results this morning
> but one of them might be stale.

```yaml
Account metadata:
  Support tier: Business
  Total checks available: 115

Check results:

  Check 1:
    Check id: prod-rdp-open-check
    Check name: Security Groups - Specific Ports Unrestricted
    Category: Security
    Status: error
    Timestamp: 2026-08-05T06:00:00Z (4 hours ago)
    Excluded resources: none
    Flagged resources:
      - resourceId: sg-prod-bastion
        region: us-east-1
        status: error
        metadata:
          Protocol: TCP
          Port: 3389
          Source: 0.0.0.0/0

  Check 2:
    Check id: prod-idle-volumes-check
    Check name: Underutilized EBS Volumes
    Category: Cost Optimization
    Status: error
    Timestamp: 2026-08-05T04:00:00Z (6 hours ago)
    Excluded resources: none
    Flagged resources:
      - resourceId: vol-prod-stale-01
        region: us-east-1
        status: error
        metadata:
          Volume Type: gp2
          Days Unattached: 12
          Estimated Monthly Savings: $45

  Check 3:
    Check id: prod-cloudtrail-check
    Check name: AWS CloudTrail Logging
    Category: Security
    Status: ok
    Timestamp: 2026-08-01T12:00:00Z (4 days ago)
    Excluded resources: none
    Flagged resources: (none)
```

## Skill output

```text
CHECK: Security Groups - Specific Ports Unrestricted (prod-rdp-open-check)
VERDICT: CRITICAL_CHECK
REASON: Security pillar check with status "error" — RDP port 3389 open to
0.0.0.0/0 on sg-prod-bastion (Step 2). Result is fresh (4 hours old).
FINDINGS:
  - [CRITICAL_CHECK] Security check status "error": port 3389 open to
    0.0.0.0/0 on sg-prod-bastion (Step 2)
REMEDIATION:
  1. Restrict sg-prod-bastion inbound rule for port 3389 to the specific
     source CIDR or security group that needs RDP access.
  2. Verify: aws ec2 describe-security-groups --group-ids sg-prod-bastion
  3. Prefer Session Manager or a bastion tunnel over exposing RDP.

CHECK: Underutilized EBS Volumes (prod-idle-volumes-check)
VERDICT: WARNING_CHECK
REASON: Cost Optimization pillar check with status "error" — vol-prod-stale-01
unattached for 12 days, $45/mo waste (Step 2). Result is fresh (6 hours old).
FINDINGS:
  - [WARNING_CHECK] Cost Optimization check status "error":
    vol-prod-stale-01 unattached 12 days, $45/mo waste (Step 2)
REMEDIATION:
  1. Snapshot the volume if data needs to be preserved: aws ec2
     create-snapshot --volume-id vol-prod-stale-01.
  2. Delete the unattached volume: aws ec2 delete-volume --volume-id
     vol-prod-stale-01.

CHECK: AWS CloudTrail Logging (prod-cloudtrail-check)
VERDICT: CONFIG_GAP
REASON: Security pillar check with status "ok" but timestamp is 4 days old
(Step 1). The ok status is unreliable — the condition may have degraded since
the last refresh. Cannot trust a 96-hour-old result for a compliance audit.
FINDINGS:
  - [CONFIG_GAP] Check result timestamp > 24 hours old (4 days). The ok
    status is stale and should not be trusted without a refresh (Step 1).
REMEDIATION:
  1. Refresh the check: aws support refresh-trusted-advisor-check
     --check-id prod-cloudtrail-check
  2. Poll refresh status until success, then re-audit.
  3. Set up a weekly refresh cadence to avoid stale results in future.
```

## What the skill caught that a generic assistant misses

1. **Category-severity matrix.** A generic assistant rates both the security
   check and the cost check as "needs attention." The skill distinguishes:
   Security error is CRITICAL_CHECK (active exposure — RDP to the internet
   is a common ransomware entry point), while Cost Optimization error is
   WARNING_CHECK (waste, not a breach vector). The operator triages the
   RDP exposure first.

2. **Staleness as a separate dimension.** The generic assistant reads "ok"
   on the CloudTrail check and says "all good." The skill catches that the
   timestamp is 4 days old — for a compliance audit, a 96-hour-old ok status
   is not trustworthy. The staleness finding is CONFIG_GAP, not OK.

3. **Support-tier awareness.** The skill notes Business support (115 checks
   available) as a precondition — it does not silently assume all checks
   are accessible. If the account were Basic, the skill would flag CONFIG_GAP
   for limited coverage even if individual checks showed ok.

4. **Per-check remediation with CLI.** The skill provides specific CLI
   commands per finding (restrict the SG, snapshot + delete the volume,
   refresh the stale check) rather than generic advice like "fix the
   security group."

## Slash-command invocation

```
/aws:audit-trustedadvisor-checks
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit these Trusted Advisor results before the compliance review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: trustedadvisor-check-auditor]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit Trusted Advisor check results"
# [Phase: Audit | Skills routed: trustedadvisor-check-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating findings, validate TA posture:

```bash
# List all available checks
aws support describe-trusted-advisor-checks --language en \
  --profile default --output json | jq '.checks[] | {name, category, id}'

# Refresh a specific check before re-audit
aws support refresh-trusted-advisor-check --check-id <id> --profile default

# Poll refresh status
aws support describe-trusted-advisor-check-refresh-statuses \
  --check-id <id> --profile default

# Get full check result with flagged resources
aws support describe-trusted-advisor-check-result --check-id <id> \
  --language en --profile default --output json
```
