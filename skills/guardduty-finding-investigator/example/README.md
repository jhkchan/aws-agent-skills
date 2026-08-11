# Example usage: guardduty-finding-investigator

A walkthrough showing the skill diagnosing a CryptoCurrency finding
that a generic assistant would misdiagnose as "restart the instance,"
demonstrating the finding-type-driven probe order, the CloudTrail +
VPC Flow Log + CloudWatch corroboration chain, the false-positive
rule-out, and the evidence-backed ROOT_CAUSE_FOUND verdict.

## Input (user prompt)

> Our SOC paged on a GuardDuty CryptoCurrency:EC2/BitcoinTool.B!DNS
> finding on i-app-1. The app team says the instance is fine — it's
> a Node.js API server, no crypto anything. We've been going back and
> forth for 20 minutes. Help us figure out if this is real or another
> false positive.

```text
Finding: a1b2c3d4 in detector 12ab34cd (us-east-1)
Type: CryptoCurrency:EC2/BitcoinTool.B!DNS, severity 7.5 (High)
Resource: i-app-1 (Node.js API server in prod VPC)

aws guardduty get-findings:
  service.action.dnsRequestAction.domain: "miningpool.example"
  service.additionalInfo.threatListName: "MiningDomains"

CloudWatch CPUUtilization on i-app-1 (last 90 min):
  Average 95.2%, Maximum 99.8%

VPC Flow Logs query (last 60 min):
  srcAddr=10.0.5.12 (i-app-1)  dstAddr=203.0.113.55  dstPort=3333
  sum(bytes) = 2.1 MB

Application dependency scan (package.json):
  no reference to "miningpool.example" or any mining library
```

## Skill output

```text
FINDING: a1b2c3d4 (CryptoCurrency:EC2/BitcoinTool.B!DNS on i-app-1)
VERDICT: ROOT_CAUSE_FOUND
REASON: i-app-1 queried a known mining-pool domain (miningpool.example)
  with sustained 95% CPUUtilization for the 90 minutes preceding the
  finding, plus outbound VPC Flow traffic on port 3333 to a Stratum pool
  endpoint (Step 5).
LAYER: CRYPTO_MINING
SEVERITY: HIGH
EVIDENCE:
  - GuardDuty finding: service.action.dnsRequestAction.domain =
    "miningpool.example", resource.instanceDetails.instanceId = i-app-1,
    severity = 7.5, threatListName = "MiningDomains".
  - CloudWatch CPUUtilization on i-app-1: Average 95.2%, Maximum 99.8%
    across the 90-minute window preceding the finding.
  - VPC Flow Logs: sustained outbound from 10.0.5.12 to 203.0.113.55
    on dstPort=3333, 2.1 MB total egress in the window.
  - FP ruled out: app on i-app-1 is a Node.js API server with no DNS
    dependency on miningpool.example; the domain is not in the
    application's dependencies or code repository. The CryptoCurrency
    detector did NOT fire on DNS alone — CPU + egress corroborate.
SUPPRESSION: Not applicable — true positive.
REMEDIATION:
  1. Isolate i-app-1 by attaching sg-quarantine (no in/out rules):
     aws ec2 modify-instance-attribute --instance-id i-app-1
       --groups sg-quarantine --profile <p>
  2. Snapshot the root EBS volume for Malware Protection scan:
     aws ec2 create-snapshots --instance-specification InstanceId=i-app-1
     aws malware-scan start-malware-scan --resource-arn <snapshot-arn>
  3. Investigate the compromise vector: IAM role on i-app-1, recent
     deployments, exposed credentials.
  4. Verify: describe-instances shows sg-quarantine; VPC Flow Logs show
     no further outbound traffic.
CONFIRM: "CONFIRM: About to modify-instance-attribute on i-app-1
  (isolate to sg-quarantine). This disconnects the app. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **DNS + CPU + egress triangulation, not DNS alone.** A generic
   assistant sees the BitcoinTool.B!DNS finding and either dismisses it
   as a domain reputation false positive or jumps straight to "restart
   the instance." The skill recognises that the `!DNS` suffix is the
   *signal* — corroboration requires CloudWatch CPU AND VPC Flow egress
   to mining-pool ports. Three independent positive probes convert a
   hypothesis into ROOT_CAUSE_FOUND.

2. **The application dependency rule-out.** The skill explicitly tests
   the false-positive class "the domain resolves to a mining pool but
   is not used for mining" by checking the package.json for any
   legitimate dependency on the domain. A generic assistant asserts
   "the app team says it's fine" without testing that claim.

3. **Containment that preserves forensic state.** The skill isolates
   the instance via SG, NOT terminate/stop — preserving memory, process
   state, and EBS for Malware Protection scan and IR. A generic
   assistant that "restarts the instance" destroys the evidence needed
   to scope the compromise.

4. **The compromise-vector investigation.** The skill points to the
   next step: how did xmrig get onto a Node.js API server? The IAM
   role, recent deployments, and exposed credentials are the entry
   vector — fixing the instance is incomplete without finding the
   entry vector.

## Slash-command invocation

```
/aws:troubleshoot-guardduty-finding
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose the High-severity CryptoCurrency finding on i-app-1"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: guardduty-finding-investigator]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After containment, scope the blast radius:

```bash
# Confirm i-app-1 is isolated
aws ec2 describe-instances --instance-ids i-app-1 \
  --profile default --output json | \
  jq '.Reservations[0].Instances[0].SecurityGroups[].GroupName'
# Expect: ["sg-quarantine"]

# Confirm VPC Flow Logs show no further outbound
aws logs start-query --log-group-name <flow-log-group> \
  --start-time $(date -u -d '-15 minutes' +%s)000 \
  --end-time $(date -u +%s)000 \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort
    | filter srcAddr="10.0.5.12" and action=ACCEPT | limit 20'

# Check other instances for the same mining-pool domain
aws guardduty get-findings-statistics --detector-id 12ab34cd \
  --finding-statistics-types COUNT_BY_TYPE \
  --finding-criteria Criterion={"type":{"Eq":["CryptoCurrency:EC2/BitcoinTool.B!DNS"]}} \
  --profile default
```

Then monitor the GuardDuty finding count for 24 hours to confirm no
new CryptoCurrency findings fire on other instances in the VPC.
