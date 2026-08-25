---
name: vpc-connectivity-troubleshooter
description: 'Diagnoses AWS VPC network connectivity issues through a systematic OSI-layered diagnostic tree: Layer 3 routing (missing route, wrong target IGW/NAT/TGW/peering/VPN, overlapping CIDRs on peered VPCs), Layer 4 security groups (stateful inbound, outbound return path, SG references that silently fail cross-VPC), Layer 4 NACLs (stateless both directions, ephemeral range 1024-65535), Layer 7 DNS (Route 53 private hosted zones, VPC DNS resolution settings), VPC endpoint policies, and application-level auth/SSL. Cross-VPC coverage: VPC peering (DNS flag, SG references), Transit Gateway (route table associations, propagation), and PrivateLink (interface endpoint NLB). Uses Reachability Analyzer and VPC Flow Logs. Emits ROOT_CAUSE_FOUND, NEED_MORE_INFO, or ESCALATE.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and topology descriptions. Live-account diagnosis uses aws ec2 describe-route-tables, aws ec2 describe-security-groups, aws ec2 describe-network-acls, aws ec2 describe-vpc-endpoints, aws ec2 describe-vpc-peering-connections, aws ec2 describe-transit- gateway-attachments, aws ec2 describe-transit-gateway-route-tables, aws ec2...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing a VPC network connectivity issue (cannot reach an endpoint, intermittent connectivity, port blocked, DNS resolution failure, cross-VPC traffic failure, VPC endpoint policy block, peering asymmetry, TGW route propagation gap), walking a symptom to the failed layer with verify and fix commands, validating why an EC2 instance / Lambda / ECS task / on-prem host cannot reach a destination, or triaging a "the network is down" page where the root cause may be routing, security groups, NACLs, DNS, endpoint policy, or cross-VPC plumbing — not necessarily the destination service itself.
  when_not_to_use: Internet egress cost audits (use vpc-flow-logs-auditor or cost- anomaly detectors), RDS-specific auth and TLS issues (use rds- connectivity-troubleshooter which specialises the L7 layer for database engines), IAM execution-role diagnostics (use iam- permission-troubleshooter), or Direct Connect / Site-to-Site VPN hardware configuration (use the carrier / device-side tooling). This skill diagnoses packet-path connectivity; it does not audit configuration posture or replace dedicated per-service troubleshooters.
  activation_triggers: VPC connection timeout, cannot reach EC2 instance, EC2 port unreachable, Lambda VPC timeout, ECS task cannot reach, security group blocking traffic, NACL dropping packets, route table missing, VPC peering not working, Transit Gateway routing, TGW routes not propagating, VPC endpoint policy blocked, DNS not resolving in VPC, Route 53 private hosted zone, cross-VPC connectivity, PrivateLink endpoint service, Reachability Analyzer, VPC Flow Logs analysis, overlapping CIDR peering, troubleshoot VPC connectivity
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "host cannot reach destination on port X", intermittent vs persistent pattern), optionally paired with the source and destination context (instance/subnet/VPC IDs, ports, protocol), OR (b) a source-destination pair plus caller context (region, AZ, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈ {ROUTE_TABLE_MISSING, ROUTE_TABLE_WRONG_TARGET, ROUTE_OVERLAPPING_CIDR, SG_INBOUND, SG_OUTBOUND, SG_REFERENCE_CROSS_VPC, NACL_STATELESS, DNS_RESOLUTION, DNS_PHZ_ASSOCIATION, ENDPOINT_POLICY, PEERING_INACTIVE, PEERING_DNS_RESOLUTION, PEERING_SG_REFERENCE, TGW_ROUTE_PROPAGATION, TGW_ASSOCIATION_MISSING, PRIVATELINK_ENDPOINT_SERVICE, PRIVATELINK_SG, APP_AUTH, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"application on EC2 instance i-app (subnet subnet-aaa,\nSG sg-app, AZ us-east-1a, VPC vpc-source) cannot reach EC2\ninstance i-db (subnet subnet-bbb, SG sg-db, AZ us-east-1b, VPC\nvpc-target) on tcp/5432. nc -vz returns 'Connection timed out'.\nThe two VPCs are peered (pcx-aaa) and the peering status is\nActive.\"\nSource: i-app, subnet-aaa (CIDR 10.0.1.0/24 in vpc-source\n  10.0.0.0/16), SG sg-app\nDestination: i-db, subnet-bbb (CIDR 172.16.1.0/24 in vpc-target\n  172.16.0.0/16), SG sg-db\nPath: same region (us-east-1), VPC peering pcx-aaa (Active)\nObserved error: nc -vz 172.16.1.10 5432 → \"Connection timed out\""
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: VPC, connectivity, routing, route table, security group, NACL, network ACL, ephemeral port, DNS, Route 53, private hosted zone, resolver, VPC endpoint, endpoint policy, VPC peering, Transit Gateway, TGW, PrivateLink, Reachability Analyzer, VPC Flow Logs, overlapping CIDR, troubleshooting
  tags: vpc, networking, troubleshooting, routing, security-groups, nacl, dns, vpc-peering, transit-gateway, privatelink
---

# VPC Connectivity Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  timeout / SYN no SYN-ACK → ROUTE_TABLE_MISSING /
  ROUTE_TABLE_WRONG_TARGET / ROUTE_OVERLAPPING_CIDR / SG_INBOUND /
  SG_OUTBOUND / NACL_STATELESS / PEERING_INACTIVE / TGW_ROUTE_PROPAGATION
  / PRIVATELINK_ENDPOINT_SERVICE; connection refused / TCP RST →
  destination port closed (instance-level, outside this skill's VPC
  scope — surface it); DNS NXDOMAIN / "server can't find" →
  DNS_RESOLUTION / DNS_PHZ_ASSOCIATION; HTTP 403 from AWS service →
  ENDPOINT_POLICY; cross-VPC success on IP but failure on hostname →
  PEERING_DNS_RESOLUTION.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_FOUND verdict
  requires positive evidence — a failing probe that matches the
  symptom — not a process of elimination that "must be the SG."
- **OSI ordering is non-negotiable.** DNS (L7) → routing (L3) → SG
  (stateful L3-L4) → NACL (stateless L4) → cross-VPC plumbing → port
  reachability (L4) → application (L7). Skipping layers produces false
  root causes.
- **Security groups are stateful; NACLs are stateless.** A SG inbound
  allow on 443 implicitly allows the return SYN-ACK. A NACL inbound
  allow on 443 ALSO requires an outbound allow on the ephemeral range
  (1024-65535) for the return packet, because NACLs evaluate each
  direction independently. Operators who "fixed the SG and still
  cannot connect" usually have a NACL denying the return path.
- **SG references (`sg-xxx`) only work within the same VPC or a peered
  VPC.** A SG rule referencing `sg-xxx` from an unrelated VPC is
  silently ignored — the rule appears valid in the console but never
  matches traffic. Use CIDR blocks or a referenced SG in the peered
  VPC (with peering in the route table).
- **ESCALATE for AWS-side incidents.** AZ-wide degradation, region-
  wide service events, and underlying host failures are not customer-
  fixable — escalate to AWS Support and surface the event ARN.

## Mindset

Mindset detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the incident-framing model.

## Philosophy

The four senior-engineer behaviours (OSI ordering, SG stateful vs NACL stateless, overlapping-CIDR silent failure, SG-reference scope) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the reasoning behind each probe-order rule.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Connection timed out`, `Operation timed out`, SYN no SYN-ACK | ROUTE_TABLE_MISSING / ROUTE_TABLE_WRONG_TARGET / ROUTE_OVERLAPPING_CIDR / SG_INBOUND / NACL_STATELESS / PEERING_INACTIVE / TGW_ROUTE_PROPAGATION | `describe-route-tables` + `describe-security-groups` + `describe-network-acls` for the source subnet |
| `Connection refused`, `ECONNREFUSED`, TCP RST after SYN | Destination port closed (instance-level — outside this skill's VPC scope) | Confirm destination instance is running and listener is bound |
| `Name or service not known`, `NXDOMAIN`, `server can't find` | DNS_RESOLUTION / DNS_PHZ_ASSOCIATION | `dig`/`nslookup` from source; `list-hosted-zones-by-vpc`; VPC DNS resolution/support settings |
| HTTP 403 / AccessDenied from an AWS service via VPC endpoint | ENDPOINT_POLICY | `describe-vpc-endpoints` (Policy, State) |
| Cross-VPC success on IP but failure on hostname | PEERING_DNS_RESOLUTION | VPC peering `AllowDnsResolutionFromRemoteVpcDomainName` flag |
| VPC peering Active but traffic times out | ROUTE_OVERLAPPING_CIDR / PEERING_SG_REFERENCE / route table missing pcx route | Compare VPC CIDRs; `describe-route-tables` for pcx route; `describe-security-groups` for SG reference scope |
| TGW attachment Active but traffic times out | TGW_ROUTE_PROPAGATION / TGW_ASSOCIATION_MISSING | `describe-transit-gateway-route-tables` for propagation; `describe-transit-gateway-attachments` for association |
| PrivateLink endpoint accepted but service unreachable | PRIVATELINK_ENDPOINT_SERVICE / PRIVATELINK_SG | `describe-vpc-endpoints` (ServiceName, State); NLB and endpoint SG allow |
| Application reaches TCP layer but auth/SSL fails | APP_AUTH | Application logs; SSL/TLS handshake details |
| None of the above, region-wide event | ESCALATE | `aws health describe-events` + AWS Service Health Dashboard |

## Pre-flight: source / destination context and AWS Health gate

Before running symptom-specific probes, gather the canonical source and
destination context and short-circuit on AWS-side events that mimic
connectivity failures. Misclassifying these produces hours of network
debugging for a problem that is not a network problem.

### Pre-flight commands

Source/destination context + AWS Health pre-flight command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before the first probe.

### Pre-flight short-circuits

| Signal | Effect |
|---|---|
| AWS Health open event for `AWS_EC2`, `AWS_VPC`, `AWS_DIRECTCONNECT` in the region | Likely AWS-side degradation. Surface in REMEDIATION; consider ESCALATE. |
| Source instance `State: stopped` or `terminated` | Not a connectivity issue; the source is gone. |
| Destination instance `State: stopped` or `terminated` | Not a connectivity issue; the destination is gone. Surface as ROOT_CAUSE_FOUND with `LAYER: APP_AUTH` (no listener) or `UNKNOWN`. |
| Destination AZ has a known AWS Health event | Traffic to that AZ may fail while cross-AZ paths succeed. Note the AZ-specific signal. |
| Source subnet `AvailableIpAddressCount: 0` | Subnet is exhausted; new ENIs cannot be created. Symptom is on ENI-creating workloads (Lambda VPC attach, ECS tasks). |

If the input is malformed (missing source or destination identifier,
absent symptom, no port/protocol for reachability diagnosis), emit:

The NEED_MORE_INFO malformed-input output template moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Emit it whenever required context is missing.

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in OSI order. Each
layer ends with either a positive root-cause confirmation (failing probe
that matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

The full Step-0 gotcha catalog (cross-VPC SG references, NACL statelessness, overlapping CIDRs, peering non-transitivity, DNS flags, PHZ association, endpoint policy vs IAM, TGW propagation, PrivateLink handshake, nc ground truth, Reachability Analyzer, Flow Logs, Lambda/IGW asymmetry, cross-AZ cost) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before diagnosing any non-trivial symptom.

### Step 1: Symptom entry — pick the diagnostic branch

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 9 (ESCALATE or
NEED_MORE_INFO).

| Symptom | Branch |
|---|---|
| `Connection timed out`, SYN no SYN-ACK, `nc -vz` hangs | Step 2 — Timeout (OSI walk) |
| `Name or service not known`, `NXDOMAIN`, hostname does not resolve | Step 3 — DNS |
| HTTP 403 from AWS service via VPC endpoint | Step 4 — VPC endpoint policy |
| Cross-VPC via peering: peering Active but traffic times out | Step 5 — VPC peering |
| Cross-VPC via TGW: attachments Active but traffic times out | Step 6 — Transit Gateway |
| Cross-VPC via PrivateLink: endpoint accepted but service unreachable | Step 7 — PrivateLink |
| TCP reaches but TLS / auth fails | Step 8 — Application |
| None of the above | Step 9 — Escalate / NEED_MORE_INFO |

### Step 2: Connection timeout — OSI-aligned diagnostic tree

Sub-steps 2a-2j — the full OSI walk (source/dest context, route tables both sides, overlapping CIDRs, SG inbound/outbound + cross-VPC SG references, NACLs in both directions on both subnets, nc/telnet probe, VPC Flow Logs, Reachability Analyzer) with every probe command and verdict condition moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when diagnosing a timeout symptom.

### Step 3: DNS resolution failure

DNS probes (resolver/DHCP options, enableDnsSupport + enableDnsHostnames, Route 53 PHZ association, Resolver endpoints and rules) with DNS_RESOLUTION / DNS_PHZ_ASSOCIATION verdict conditions moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when a hostname does not resolve.

### Step 4: VPC endpoint policy

Endpoint-policy probes (describe-vpc-endpoints policy read, endpoint bypass test) with ENDPOINT_POLICY verdict conditions moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand on AccessDenied that clears outside the VPC.

### Step 5: VPC peering — Active but traffic times out

Peering probes (status table, both-side pcx routes, overlapping CIDRs, cross-VPC SG references, remote DNS resolution flag) with PEERING_* verdict conditions moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when peering is Active but traffic times out.

### Step 6: Transit Gateway — attachments Active but traffic times out

TGW probes (attachment state, TGW route-table association vs propagation, both-side tgw routes) with TGW_ASSOCIATION_MISSING / TGW_ROUTE_PROPAGATION verdict conditions moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when attachments are Active but traffic times out.

### Step 7: PrivateLink — endpoint accepted but service unreachable

PrivateLink probes (endpoint state, endpoint-SG ENI, provider endpoint service + NLB health, private DNS) with PRIVATELINK_* verdict conditions moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when an endpoint is accepted but the service is unreachable.

### Step 8: Application layer — TLS / auth

APP_AUTH routing guidance (TLS/auth symptoms route to the application-specific troubleshooters) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when TCP succeeds but TLS or auth fails.

### Step 9: Escalate or NEED_MORE_INFO

ESCALATE / NEED_MORE_INFO exit rules (AWS-side incidents, missing operator input) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when no layer produced a positive match.

## Output format

```text
TARGET: <source → destination pair>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROUTE_TABLE_MISSING | ROUTE_TABLE_WRONG_TARGET |
        ROUTE_OVERLAPPING_CIDR | SG_INBOUND | SG_OUTBOUND |
        SG_REFERENCE_CROSS_VPC | NACL_STATELESS | DNS_RESOLUTION |
        DNS_PHZ_ASSOCIATION | ENDPOINT_POLICY | PEERING_INACTIVE |
        PEERING_DNS_RESOLUTION | PEERING_SG_REFERENCE |
        TGW_ROUTE_PROPAGATION | TGW_ASSOCIATION_MISSING |
        PRIVATELINK_ENDPOINT_SERVICE | PRIVATELINK_SG | APP_AUTH |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <id> in <region>. Proceed?
  (yes/no)"
```

### Worked example — SG inbound missing rule

```text
TARGET: i-app (10.0.1.10, subnet-aaa, vpc-source) → i-db
  (172.16.1.10, subnet-bbb, vpc-target) on tcp/5432
VERDICT: ROOT_CAUSE_FOUND
REASON: The destination SG sg-db has no inbound rule matching the
  source's CIDR 10.0.1.0/24 on port 5432 — the SYN is dropped at the
  instance's security group (Step 2e).
LAYER: SG_INBOUND
EVIDENCE:
  - Symptom: application on i-app (10.0.1.10) reports "Operation
    timed out" when connecting to i-db (172.16.1.10:5432). nc -vz
    hangs.
  - Probe: aws ec2 describe-security-groups --group-ids sg-db returns
    inbound rules allowing 172.16.0.0/16 (local VPC) on 5432. No
    rule matches 10.0.1.0/24 (source VPC CIDR).
  - Passing: route table for subnet-aaa has a pcx-aaa route to
    172.16.0.0/16; route table for subnet-bbb has a pcx-aaa route
    back to 10.0.0.0/16; peering pcx-aaa is Active; VPC CIDRs do not
    overlap; NACL on both subnets is the default (allow all).
REMEDIATION:
  1. Add an inbound rule to sg-db allowing the source CIDR on tcp/5432:
     aws ec2 authorize-security-group-ingress --group-id sg-db
       --protocol tcp --port 5432 --cidr 10.0.1.0/24 --profile <p>
  2. Verify from the source: nc -vz 172.16.1.10 5432 (should succeed
     within 1s).
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-db in
   us-east-1 for 10.0.1.0/24 on tcp/5432. Proceed? (yes/no)"
```

### Worked example — NACL missing ephemeral outbound

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a NACL_STATELESS verdict.

### Worked example — overlapping CIDR (silent peering failure)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a ROUTE_OVERLAPPING_CIDR verdict.

### Worked example — VPC endpoint policy blocking S3 PutObject

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting an ENDPOINT_POLICY verdict.

## STRICT output contract

This contract is mandatory. The Output format template above is the
authoritative structure; the rules below disambiguate the failure
modes that score D8=13 on this skill. Violating any rule is a
misdiagnosis.

### Required output structure

Every diagnosis MUST emit this exact block, with all fields populated
(no empty fields, no omitted sections, no reordering):

The literal block template is the one in ## Output format above; this annotated duplicate moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when the contract wording is unclear.

Verdict-specific rules:
- `ROOT_CAUSE_FOUND` → LAYER is one of the 18 enum values; EVIDENCE
  includes a failing probe whose output positively confirms the cause
  (not a process of elimination); REMEDIATION is actionable CLI.
- `NEED_MORE_INFO` → LAYER is `UNKNOWN` or the best candidate; EVIDENCE
  lists the missing input (source ID, destination ID, port, protocol,
  region) and the next probe to run once it is supplied.
- `ESCALATE` → LAYER is the suspected AWS-side category; REASON cites
  the AWS Health event ARN or the carrier/out-of-band signal.

### FORBIDDEN output patterns

1. NEVER skip the NACL check — NACLs are stateless, both inbound AND
   outbound rules needed for ephemeral ports 1024-65535. A diagnosis
   that omits `describe-network-acls` for both source and destination
   subnets is incomplete, even if a SG rule matches.
2. NEVER assume a Security Group reference works cross-VPC — SG
   references (`sg-xxx`) only resolve within the same VPC or a peered
   VPC with peering in the route table, not via Transit Gateway. A
   cross-VPC SG reference via TGW is silently ignored.
3. NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
   the symptom. "It must be the SG" by process of elimination is
   forbidden — cite the `describe-security-groups` or `nc -vz` output
   that positively confirms the drop.
4. NEVER skip the OSI order for timeout symptoms. The probe order is
   DNS (L7) → routing (L3) → SG (L4) → NACL (L4) → cross-VPC plumbing
   → port reachability → application. A diagnosis that checks the SG
   before the route table and concludes "SG is fine" missed that the
   SYN never reached the SG evaluation.
5. NEVER treat VPC peering as transitive. Peering between A-B and B-C
   does NOT allow A to reach C via B — transit requires Transit
   Gateway. A diagnosis that suggests "add a peering route through
   VPC-B" is wrong.
6. NEVER assume overlapping VPC CIDRs will route via peering. They are
   a silent failure: the `pcx-xxx` route appears in the table but
   packets do not deliver. A diagnosis that lists peering Active +
   route present as "passing" without comparing the two VPC CIDRs is
   incomplete.
7. NEVER assume the VPC endpoint policy matches the IAM policy. The
   endpoint policy is an independent layer that can deny actions IAM
   allows. A diagnosis that clears IAM without bypassing the endpoint
   to verify has not ruled out `ENDPOINT_POLICY`.

### Perfect example output

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a complete ROOT_CAUSE_FOUND verdict.

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches
  the symptom. A "process of elimination" diagnosis erodes operator
  trust when the real cause is elsewhere.

- NEVER skip the OSI order for timeout symptoms. If you check the
  security group before the route table and conclude "the SG is fine,
  must be the destination," you missed that the route table has no
  route for the destination CIDR — the SYN never reached the SG
  evaluation.

- NEVER evaluate NACLs in only one direction. NACLs are stateless;
  the return SYN-ACK is a separate evaluation. The most common NACL
  mistake is an inbound rule on 443 with no outbound rule on the
  ephemeral range (1024-65535).

- NEVER assume a security-group reference (`sg-xxx`) works cross-VPC.
  Cross-VPC SG references are silently ignored unless the VPCs are
  peered AND the peering is in the route table. Use CIDR blocks or a
  referenced SG in the peered VPC.

- NEVER treat VPC peering as transitive. Peering between A-B and B-C
  does NOT allow A to reach C via B. Transit requires Transit Gateway.

- NEVER assume overlapping VPC CIDRs will route via peering. They are
  a silent failure — the route appears but packets do not deliver.

- NEVER assume the VPC DNS settings are correct because "DNS works
  for some queries." Route 53 private hosted zones require BOTH
  `enableDnsSupport` AND `enableDnsHostnames` to be true. Cross-
  account PHZs require explicit association with the consumer VPC.

- NEVER assume the VPC endpoint policy matches the IAM policy. The
  endpoint policy is an independent layer; it can deny actions that
  IAM allows. Bypass the endpoint to verify.

- NEVER assume `PrivateDnsEnabled: true` on an interface endpoint is
  cosmetic. Without it, the service's DNS name resolves to the public
  IP and traffic routes over the internet instead of the endpoint.

- NEVER conclude "the network is flaky" without running `nc -vz` or
  equivalent from the source host at least three times. Intermittent
  packet loss is rare in VPC; intermittent failures are usually
  stateful (DNS cache, connection pool, failover) not packet-loss.

- NEVER assume Transit Gateway route propagation is automatic. Each
  attachment must be associated with a TGW route table AND propagate
  its routes. Association alone does not propagate.

- NEVER assume PrivateLink endpoint service availability implies NLB
  health. The endpoint can be `available` while the NLB has no
  healthy targets in the consumer's AZ. Always check NLB target
  health.

- NEVER recommend modifying a NACL to deny specific traffic as a
  security fix without checking the existing rule order. NACLs
  evaluate lowest-to-highest rule number; first match wins. A new
  deny at rule 200 is shadowed by an existing allow at rule 100.

- NEVER recommend expanding a CIDR to `0.0.0.0/0` to "fix" a SG
  issue. This exposes the listener to the entire internet. Use the
  narrowest scope that covers the legitimate source.

- NEVER rely on Reachability Analyzer as the sole evidence. It models
  the configured state; it does not test the live packet. Pair it
  with `nc -vz` from the source host.

- NEVER skip VPC Flow Logs when diagnosing intermittent issues. Flow
  Logs with `action: REJECT` confirm the packet was dropped by SG or
  NACL; `action: ACCEPT` confirms the packet reached the ENI.

## Pre-flight safety checks (run before any state-changing CLI)

Pre-flight safety checks (confirmation gate, read-only-first, SG/NACL/route/peering/TGW/endpoint blast-radius rules, bulk batch limit) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand before any state-changing CLI.

## Remediation guidance

Per-LAYER remediation commands for all 17 layer values (create-route, replace-route, SG ingress/egress, NACL ephemeral entries, DNS attributes, PHZ association, endpoint policy, peering accept/DNS options, TGW propagation/association, PrivateLink NLB/SG) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when writing the REMEDIATION block.

## Deep reference: VPC connectivity layer model

Layer model, SG-vs-NACL comparison, VPC peering vs Transit Gateway, and VPC endpoint type tables moved verbatim to [references/connectivity-layer-reference.md](references/connectivity-layer-reference.md).
Load on demand for the comparison tables.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to check what changed in the last 24 months.

## References (load on demand)

- [Diagnostic commands](references/diagnostic-commands.md) — pre-flight context commands and the full Step 2-9 diagnostic walk with every probe command and verdict condition
- [Worked examples](references/worked-examples.md) — secondary worked examples (NACL ephemeral outbound, overlapping CIDR, endpoint policy), the NEED_MORE_INFO re-prompt template, and annotated output-contract templates
- [Error handling](references/error-handling.md) — pre-flight safety checks before state-changing CLIs and per-LAYER remediation guidance with fix and verify commands
- [Advanced patterns](references/advanced-patterns.md) — mindset, philosophy, Step-0 non-obvious behaviours, and recent AWS features (2024-2026)
- [Connectivity layer reference](references/connectivity-layer-reference.md) — ports and protocol semantics, SG/NACL evaluation, peering/TGW/PrivateLink specifics, plus the moved layer-model comparison tables

## Domain

AWS CloudOps / VPC Networking, Routing, Security Groups, NACLs, DNS,
Cross-VPC Connectivity (Peering, Transit Gateway, PrivateLink), and
Packet-Path Diagnostics.

## AWS documentation

- **Amazon VPC User Guide** — https://docs.aws.amazon.com/vpc/latest/userguide/
- **VPC route tables** — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- **Security groups** — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html
- **Network ACLs** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- **VPC peering** — https://docs.aws.amazon.com/vpc/latest/peering/Welcome.html
- **Transit Gateway** — https://docs.aws.amazon.com/vpc/latest/tgw/What_is_TGW.html
- **AWS PrivateLink** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **VPC endpoints** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html
- **Reachability Analyzer** — https://docs.aws.amazon.com/vpc/latest/reachability/What-is-Reachability-Analyzer.html
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **Route 53 Resolver** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
