# Eval prompt: permissive-wildcard-stateful-pass

Audit the following AWS Network Firewall configuration for security exposure.
Emit the standard VERDICT block (FIREWALL, VERDICT, REASON, FINDINGS,
REMEDIATION).

Firewall name: fw-permissive-wildcard-stateful-pass
Firewall ARN: arn:aws:network-firewall:us-east-1:111111111111:firewall/fw-permissive-wildcard-stateful-pass

Firewall policy:

```json
{
  "StatelessDefaultActions": ["aws:forward_to_sfe"],
  "StatelessFragmentDefaultActions": ["aws:forward_to_sfe"],
  "StatefulDefaultActions": ["aws:drop_strict"],
  "TLSInspectionConfigurationArn": "arn:aws:network-firewall:us-east-1:111111111111:tls-inspection-config/tls-prod",
  "StatefulRuleGroupReferences": [
    {
      "ResourceArn": "arn:aws:network-firewall:us-east-1:111111111111:stateful-rulegroup/allow-baseline",
      "Priority": 1
    }
  ],
  "StatelessRuleGroupReferences": []
}
```

Stateful rule group "allow-baseline" (STRICT_ORDER):

```json
{
  "RulesSource": {
    "RulesString": "pass ip any any -> any any\ndrop ip 10.0.0.0/8 any -> any 22\n"
  },
  "RuleOrder": "STRICT_ORDER"
}
```

Route table for app-subnet (rtb-aaa):

```
10.0.0.0/16  -> local
0.0.0.0/0    -> eni-firewall-az1  (firewall ENI in AZ1)
```

Logging configuration:

```
AlertLogs: enabled (CloudWatchLogs fw-alerts)
FlowLogs: enabled (CloudWatchLogs fw-flow)
```
