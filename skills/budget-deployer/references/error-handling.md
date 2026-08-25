# Error Handling (load on demand) — AWS Budget Deployer

Deployment failure triage moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (quick triage) (moved from SKILL.md)

- **`InvalidParameterException` on `create-budget-action`:** role missing
  or trust policy lacks `budgets.amazonaws.com`; policy ARN / target
  principal does not exist; cross-account role not in linked account.
- **`create-notification` succeeds but alerts never fire:** SNS
  subscription is `PendingConfirmation`; topic policy lacks
  `budgets.amazonaws.com` principal; customer-CMK key policy lacks
  `kms:GenerateDataKey*` for `budgets.amazonaws.com`.
- **Cost Anomaly subscription created but no alerts fire:** monitor not
  `ACTIVE`; topic policy lacks `ce.amazonaws.com` principal; subscription
  `Threshold` set above actual impact; monitor <7 days old (needs ~30
  days of CE history).
- **Budget action fires but does not take effect:** role lacks
  `iam:AttachUserPolicy` / `ssm:StartAutomationExecution`;
  `ApprovalModel=MANUAL` and nobody approved it; target resource in a
  different account than the ExecutionRoleArn.
