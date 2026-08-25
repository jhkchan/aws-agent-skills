# Worked Examples — Security Hub Finding Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — CIS.1.3 NOT_AVAILABLE StatusReason

```text
FINDING: arn:aws:securityhub:us-east-1:111:finding/def (CIS.1.3 access-key age)
VERDICT: ROOT_CAUSE_FOUND
REASON: The CIS.1.3 finding is NOT_AVAILABLE because the Config rule
  Lambda errored on a missing iam:GetCredentialReport permission. The
  keys themselves are compliant; the failure is in the evaluation layer
  (Step 8).
LAYER: AWS_SIDE
SEVERITY: MEDIUM
STANDARD: CIS
EVIDENCE:
  - Security Hub finding: Compliance.Status = NOT_AVAILABLE,
    Compliance.StatusReasons[0].ReasonCode = CONFIG_EVALUATION_ERROR.
  - Probe: describe-config-rules on securityhub-cis-1-3 shows
    LastEvaluationTime 26 hours ago.
  - Probe: filter-log-events on the rule's log group shows
    "AccessDenied: iam:GetCredentialReport".
  - FP ruled out: get-credential-report shows all active keys rotated
    within 60 days — the resource state is compliant.
SUPPRESSION: Not applicable — fix the rule Lambda IAM policy.
REMEDIATION:
  1. Attach iam:GetCredentialReport to the rule's IAM role:
     aws iam put-role-policy --role-name <rule-role>
       --policy-document file://iam-getcredential-allow.json
  2. Trigger re-evaluation:
     aws configservice start-config-rules-evaluation
       --config-rule-names securityhub-cis-1-3
  3. Verify: get-findings on CIS.1.3 returns Compliance.Status=PASSED
     within 5-15 minutes.
CONFIRM: "CONFIRM: About to attach iam:GetCredentialReport and trigger
  re-evaluation. Proceed? (yes/no)"
```

