# Eval prompt: ok-clean-firewall

Audit the following AWS Network Firewall configuration for security exposure.
Emit the standard VERDICT block (FIREWALL, VERDICT, REASON, FINDINGS,
REMEDIATION).

Firewall name: fw-ok-clean-firewall
Firewall ARN: arn:aws:network-firewall:us-east-1:111111111111:firewall/fw-ok-clean-firewall

Firewall policy:

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:forward_to_sfe"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": "arn:aws:network-firewall:us-east-1:111111111111:tls-inspection-config/tls-prod",
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/threat-blocks",
      "Priority": 1
    }
  ],
  "StatelessRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateless-rulegroup/known-bad-ips",
      "Priority": 1
    }
  ]
}
```

Stateful rule group "threat-blocks" (STRICT_ORDER):

```json
{
  "RulesSource": {
    "RulesString": "drop ip any any -> [198.51.100.0/24, 203.0.113.0/24] any\n"
  }
}
```

Stateless rule group "known-bad-ips" (capacity 100, consumed 5):

```json
{
  "RulesSource": {
    "StatelessRulesAndStructs": [
      {
        "Priority": 1,
        "RuleDefinition": {
          "Actions": ["aws:drop"],
          "MatchAttributes": {
            "Sources": [{"AddressDefinition": "192.0.2.0/24"}],
            "Destinations": [{"AddressDefinition": "0.0.0.0/0"}]
          }
        }
      }
    ]
  }
}
```

Route table for app-subnet (rtb-ggg):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> eni-firewall-az1  (firewall ENI in AZ1)
```

Route table for fw-subnet (rtb-hhh):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> igw-0abc123def456
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```
