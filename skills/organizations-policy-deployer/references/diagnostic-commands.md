# Diagnostic Commands — Organizations Policy Deployer

Verification and pre-flight command listings. Loaded on demand by the skill.

## Step 11 — verify effective policy & policy simulation

**Verify effective policy at any target:**

```bash
aws organizations list-policies-for-target --target-id 111122223311 \
  --filter SERVICE_CONTROL_POLICY --query 'Policies[*].{Name:Name,Id:Id}' --output table
aws organizations list-parents --child-id 111122223311   # trace OU chain
```

**Policy simulation:** the IAM `simulate-custom-policy` /
`simulate-principal-policy` APIs simulate IAM, NOT SCPs. Use
them as a pre-attach hint; the source of truth is post-attach
CloudTrail observation.

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111122223311:role/SCPTestRole \
  --action-names organizations:LeaveOrganization cloudtrail:DeleteTrail \
  --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}' --output table
```

## Step 13 — CloudTrail query for SCP-denied actions


SCP-denied API calls surface in CloudTrail as
`eventType: AwsApiCall` with
`errorCode: Client.UnauthorizedOperation` and a diagnostic in
`additionalEventData` indicating the SCP match.

```bash
# CloudTrail Logs Insight query for SCP-blocked calls (last 24h)
aws logs start-query \
  --log-group-name <org-trail-log-group> \
  --start-time $(($(date +%s) - 86400))000 \
  --end-time   $(date +%s)000 \
  --query-string 'fields @timestamp, eventName, awsAccountId, userIdentity.arn
| filter errorCode = "UnauthorizedOperation"
| filter organizationalAccessCheckDecision = "Denied"
| sort @timestamp desc | limit 50'
```

Without an Organization-level CloudTrail trail, SCP denials are
NOT centrally visible — each member account logs to its own
trail.
