# Eval: wcu-budget-exceeded

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — too many managed rule groups + custom regex rules; total WCU exceeds 1500

## Prompt

Create a Web ACL with AWSManagedRulesCommonRuleSet,
AWSManagedRulesSQLiRuleSet, AWSManagedRulesLinuxRuleSet,
AWSManagedRulesWindowsRuleSet, AWSManagedRulesUnixRuleSet,
AWSManagedRulesPHPRuleSet, AWSManagedRulesWordPressRuleSet,
AWSManagedRulesBotControlRuleSet, AWSManagedRulesATPRuleSet,
and 20 custom regex pattern set match rules. Account
123456789012, region us-east-1, scope CLOUDFRONT.
