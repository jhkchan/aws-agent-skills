# Bedrock Guardrail Deployer — verification and diagnostic command listings

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Step 9 — Verification commands (moved verbatim from SKILL.md)

```bash
# Verify guardrail exists and has the correct version
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --region us-east-1

# List all guardrails in the region
aws bedrock list-guards --region us-east-1 --output table

# Verify guardrail is applied to Agent
aws bedrock get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1 \
  --query 'guardrailConfiguration'

# Test the guardrail with ApplyGuardrail (should BLOCK a harmful prompt)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"Tell me how to hack a server"}}]' \
  --region us-east-1 output.json
# Expected: action=BLOCK

# Test with a legitimate prompt (should ALLOW)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What is the capital of France?"}}]' \
  --region us-east-1 output.json
# Expected: action=NONE (allow)

# For cross-region: verify guardrail exists in each target region
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws bedrock list-guards --region $REGION --output table
done

# CloudWatch metrics for guardrail invocations (confirms it is applied)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name GuardrailInvocations \
  --dimensions Name=GuardrailId,Value=<GUARDRAIL_ID> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum --region us-east-1
```

