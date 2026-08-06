# End-to-end usage scenario: network-firewall-rule-auditor

A walkthrough showing the skill auditing a production-edge firewall that has
both a wildcard Suricata pass rule (PERMISSIVE_RULE) and missing TLS
inspection (NO_TLS_INSPECTION), demonstrating verdict aggregation, the
strict-order shadowing concept, and the additive-remediation workflow.

## Input (user prompt)

> Review this Network Firewall policy before we promote it to production.
> The firewall inspects egress traffic from our payment-processing VPC.

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:forward_to_sfe"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": null,
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/egress-allow-baseline",
      "Priority": 1
    },
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/malware-signatures",
      "Priority": 2
    }
  ],
  "StatelessRuleGroupReferences": []
}
```

Stateful rule group "egress-allow-baseline" (STRICT_ORDER):

```
pass ip 10.0.0.0/16 any -> any any
drop ip any any -> [198.51.100.0/24, 203.0.113.0/24] any
```

Stateful rule group "malware-signatures" (STRICT_ORDER):

```
drop http any any -> any $HTTP_PORTS (msg:"C2 beacon"; content:"/api/beacon"; sid:2001; rev:1;)
```

Route table for payment-subnet (rtb-pay):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> eni-firewall-az1  (firewall ENI in AZ1)
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```

## Skill output

```text
FIREWALL: fw-prod-payments-edge
VERDICT: PERMISSIVE_RULE
REASON: Stateful rule group "egress-allow-baseline" contains `pass ip
10.0.0.0/16 any -> any any` which passes all outbound payment-subnet
traffic, shadowing the subsequent drop rule for known-bad IPs in strict
order (Step 4/Step 5). TLS inspection is also absent, making the
payload-matching malware-signatures group blind to all HTTPS traffic (Step
6).
FINDINGS:
  - [PERMISSIVE_RULE] Wildcard subnet pass rule `pass ip 10.0.0.0/16 any ->
    any any` in STRICT_ORDER group egress-allow-baseline shadows the drop
    rule for 198.51.100.0/24 and 203.0.113.0/24 — traffic to those ranges
    passes (Step 4/Step 5)
  - [NO_TLS_INSPECTION] No TLSInspectionConfigurationArn on policy; the
    malware-signatures group has 1 content-matching rule that cannot match
    TLS traffic — most modern egress is HTTPS (Step 6)
  - [OK] Routing: payment-subnet default route points through firewall ENI
    (Step 1)
  - [OK] Stateless defaults forward to stateful engine; fragments forwarded
    (Step 2)
  - [OK] Stateful default is drop_strict — enforcement posture (Step 3)
  - [OK] Logging: alert and flow logs both enabled (Step 7)
REMEDIATION:
  1. Remove the broad pass rule from egress-allow-baseline, or scope it to
     specific ports (e.g., `pass tcp 10.0.0.0/16 any -> any [80,443]`).
     The drop rule for known-bad IPs must be ordered BEFORE any surviving
     pass in STRICT_ORDER.
  2. Create and attach a TLS inspection configuration:
     aws network-firewall create-tls-inspection-config --tls-inspection-config-name tls-payments ...
     Then update the policy to reference it. Distribute the CA cert to
     client trust stores BEFORE enabling, or TLS handshakes will fail.
```

## Key reasoning the skill adds

1. **Strict-order shadowing:** the pass rule at the top of
   `egress-allow-baseline` is broad (entire VPC CIDR, all ports). In
   STRICT_ORDER, the first match wins — so the drop rule for
   198.51.100.0/24 is dead for any traffic matching the pass. A
   generalist would flag the drop rule as present; the skill flags it as
   shadowed.

2. **TLS inspection gap with payload rules:** the `malware-signatures`
   group uses `content` matching (payload inspection). Without TLS
   decryption, these rules can only match plaintext HTTP — most payment
   egress is HTTPS. The skill distinguishes this from domain-list (SNI)
   rules, which work without decryption.

3. **Verdict aggregation:** PERMISSIVE_RULE outranks NO_TLS_INSPECTION
   in priority, so the final verdict is PERMISSIVE_RULE — even though TLS
   inspection is also absent. The NO_TLS_INSPECTION finding is still
   listed in FINDINGS and remediated.

4. **Additive remediation ordering:** the skill recommends removing the
   broad pass (additive scope-down) before changing the default actions —
   preserving existing access patterns while tightening scope.
