# End-to-end usage scenario: guardduty-finding-severity-triage

A walkthrough showing the skill triaging a batch of GuardDuty findings
from a production account — including a CRITICAL compromise, a
LIKELY_FALSE_POSITIVE from an authorized scanner, and a MEDIUM behavioral
anomaly. This exercises false-positive override (Step 1 / FP-1),
threat-category escalation (Step 2), behavioral anomaly classification
(Step 4), and multi-finding aggregation.

## Input (user prompt)

> We just got a batch of GuardDuty findings from our production account.
> Triage them and tell me which ones need immediate attention:

```
Finding 1:
  Finding type: Impact:EC2/CryptocurrencyClient!SSH
  Severity: 8.0
  Resource: i-0prodweb9988 (production-web-server)
  Destination: 198.51.100.42 (mining pool: xmr.pool.minero.net)
  Count: 12, Confidence: HIGH
  Context: Production web server, no maintenance window

Finding 2:
  Finding type: Recon:EC2/PortSweepUnusual
  Severity: 6.0
  Resource: i-0scanner01 (tagged: security-scanner-nessus)
  Source IP: 10.0.5.20 (approved pentest CIDR 10.0.5.0/24)
  Ports swept: 22,80,443,445,3389,1521,3306,5432,6379,8080,8443
  Count: 1, Confidence: MEDIUM
  Context: Organization's Nessus vulnerability scanner

Finding 3:
  Finding type: UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation
  Severity: 5.0
  Resource: AIDACKCEVSQ6C2EXAMPLE (jacky.chan)
  Login location: Lagos, Nigeria (usual: Singapore, Hong Kong)
  MFA used: Yes, Count: 1, Confidence: MEDIUM
  Context: No documented travel or change window
```

## Skill output

```text
FINDING: Impact:EC2/CryptocurrencyClient!SSH
VERDICT: CRITICAL
REASON: Step 2 (active compromise) — confirmed crypto-mining client on EC2
        instance i-0prodweb9988 communicating with mining pool
        xmr.pool.minero.net. GuardDuty severity 8.0 escalated to CRITICAL
        because crypto mining confirms active compromise requiring immediate
        incident response — the attacker has command execution on the
        instance and every minute of delay increases blast radius.
REMEDIATION: Isolate the instance immediately — attach a quarantine security
             group with no inbound rules (preserve the instance for
             forensics, do NOT terminate). Capture an EBS snapshot for
             evidence. Revoke the instance-profile credentials. Trace
             lateral movement via CloudTrail (all API calls by this
             principal in the last 24h). Notify the IR team.

FINDING: Recon:EC2/PortSweepUnusual
VERDICT: LIKELY_FALSE_POSITIVE
REASON: Step 1 / FP-1 (authorized security scanner) — the source instance
        i-0scanner01 is tagged as the organization's Nessus vulnerability
        scanner, the source IP 10.0.5.20 is within the approved pentest
        CIDR 10.0.5.0/24, and the swept ports (22,80,443,...) match a
        comprehensive vulnerability-scan profile. Numeric severity 6.0 is
        overridden by the authorized-scanner context.
REMEDIATION: Archive the finding. Add 10.0.5.0/24 to GuardDuty's Trusted IP
             list (aws guardduty update-ip-set) to suppress future findings
             of this type from the scanner.

FINDING: UnauthorizedAccess:IAMUser/ConsoleLoginFromAnomalousLocation
VERDICT: MEDIUM
REASON: Step 4 (behavioral anomaly) — console login from Lagos, Nigeria for
        user jacky.chan whose usual locations are Singapore and Hong Kong.
        No false-positive override applies (no documented change window or
        travel). MFA was used, which reduces but does not eliminate risk.
        Investigate within 24 hours.
REMEDIATION: Contact jacky.chan to verify the login. Check CloudTrail for
             API calls from IP 105.112.0.55 in the same session. If the
             user does not recognize the login, deactivate all access keys
             and reset the password immediately. If confirmed legitimate,
             document the travel to prevent re-triggering.

RESOURCE: i-0prodweb9988
WORST VERDICT: CRITICAL (from CryptocurrencyClient finding)
```

## What the skill caught that a generic assistant misses

1. **Threat-category escalation from HIGH to CRITICAL.** A generic
   assistant reads severity 8.0 and calls it "HIGH." The skill's Step 2
   recognises that `Impact:EC2/CryptocurrencyClient` is an active-compromise
   indicator that requires CRITICAL triage — the numeric severity reflects
   the threat family, not the operational urgency. The instance is being
   used for crypto mining RIGHT NOW.

2. **False-positive override before severity classification.** A generic
   assistant sees severity 6.0 on the port-sweep finding and classifies it
   as MEDIUM — then tells the user to "investigate whether the scanner is
   authorized." The skill's Step 1 / FP-1 checks the authorized-scanner
   context FIRST, classifies as LIKELY_FALSE_POSITIVE, and provides the
   specific suppression-filter remediation. This saves the SOC from chasing
   every scanner-triggered finding.

3. **Forensic-first remediation ordering.** A generic assistant often says
   "terminate the compromised instance." The skill explicitly states
   "isolate, do NOT terminate" — termination destroys volatile memory
   evidence. The correct order is isolate -> snapshot -> investigate ->
   rebuild. This distinction is critical for incident response.

4. **MFA context in the MEDIUM finding.** A generic assistant might see
   "MFA used" and dismiss the finding. The skill notes that MFA reduces
   but does not eliminate risk — MFA tokens can be phished, and session
   hijacking after MFA is a known attack vector. The verdict stays MEDIUM
   with a 24-hour investigation SLA.

## Slash-command invocation

```
/aws:triage-guardduty-findings
```

Or via the orchestrator:

```
/aws:pipeline
You: "triage these GuardDuty findings from production"
```

The orchestrator emits
`[Phase: Prioritize | Skills routed: guardduty-finding-severity-triage]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "triage these guardduty findings"
# [Phase: Prioritize | Skills routed: guardduty-finding-severity-triage]
```

## Live-account invocation (optional, requires AWS CLI)

Fetch findings directly from GuardDuty for triage:

```bash
# List all ACTIVE findings, sorted by severity
aws guardduty list-findings \
  --detector-id <detector-id> \
  --finding-criteria '{"criterion": {"service.archived": {"eq": ["false"]}}}' \
  --sort-criteria '{"attributeName": "severity", "orderBy": "DESC"}' \
  --profile default

# Get full finding details for triage
aws guardduty get-findings \
  --detector-id <detector-id> \
  --finding-ids <finding-id-1> <finding-id-2> \
  --profile default
```

After triage, archive false-positive findings:

```bash
aws guardduty archive-findings \
  --detector-id <detector-id> \
  --finding-ids <fp-finding-id> \
  --profile default
```
