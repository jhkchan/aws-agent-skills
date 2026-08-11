# End-to-End Example: Bedrock Guardrail Deployment (Customer App)

A walkthrough showing how to use the `bedrock-guardrail-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying an Amazon Bedrock Guardrail for a customer-facing
LLM application powered by a Bedrock Agent. The guardrail must filter
harmful content (sexual, violence, hate, insults), block PII (email,
phone, SSN, credit card), deny specific topics (financial advice,
medical diagnosis), and include contextual grounding checks. The
workload operates in us-east-1.

- Guardrail name: `customer-app-guardrail`
- Region: `us-east-1`
- KMS key: `arn:aws:kms:us-east-1:111111111111:key/abc-123`
- Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM, insults=MEDIUM
- Denied topics: Financial_Advice, Medical_Diagnosis
- Word filters: managed PROFANITY + custom words
- PII filters: BLOCK for EMAIL, PHONE, SSN, CREDIT_DEBIT_CARD_NUMBER
- Contextual grounding: GROUNDING=0.75, RESPONSE_RELEVANCE=0.75
- Applied to: Agent `agt-xyz`
- Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-bedrock-guardrail
```

Then paste the guardrail requirements.

### Option B: Natural language

> Create a Bedrock Guardrail called customer-app-guardrail in
> us-east-1. Set content filters: sexual HIGH, violence MEDIUM, hate
> MEDIUM, insults MEDIUM. Add denied topics for Financial_Advice and
> Medical_Diagnosis. Block PII: EMAIL, PHONE, SSN,
> CREDIT_DEBIT_CARD_NUMBER. Add managed profanity and custom words.
> Enable contextual grounding at 0.75. Apply it to Agent agt-xyz.
> Use KMS key abc-123.

---

## Step 2 — Skill pre-flight

The skill validates prerequisites:

1. Model access confirmed in `us-east-1`
2. Guardrail name is valid (3-128 chars, alphanumeric)
3. KMS key exists in `us-east-1`
4. Content filter severity levels specified for all categories
5. Denied topics have definitions and examples
6. PII entities have explicit BLOCK action (not AUDIT)
7. Application target (Agent `agt-xyz`) exists
8. Contextual grounding thresholds set

All prerequisites pass.

---

## Step 3 — Expected output

```text
GUARDRAIL_SPEC: customer-app-guardrail
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Model access: confirmed in region us-east-1 (anthropic.claude-3-5-sonnet-20241022-v2:0)
  [✓] Guardrail created: id=abc123def, version=1, KMS=arn:aws:kms:us-east-1:111111111111:key/abc-123
  [✓] Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM, insults=MEDIUM (input+output)
  [✓] Denied topics: 2 topics defined (Financial_Advice, Medical_Diagnosis) with definitions and examples
  [✓] Word filters: managed=PROFANITY, custom=3 words
  [✓] PII filters: BLOCK=[EMAIL, PHONE, SSN, CREDIT_DEBIT_CARD_NUMBER], AUDIT=[], regex=0 patterns
  [✓] Contextual grounding: GROUNDING=0.75, RESPONSE_RELEVANCE=0.75
  [✓] Guardrail applied: target=Agent agt-xyz (guardrailId=abc123def, version=1)
  [✓] Cross-region: single-region (us-east-1)
VERIFICATION_COMMANDS:
  aws bedrock get-guardrail --guardrail-identifier abc123def --guardrail-version 1 --region us-east-1
  aws bedrock get-agent --agent-id agt-xyz --region us-east-1 --query 'guardrailConfiguration'
  aws bedrock apply-guardrail --guardrail-identifier abc123def --guardrail-version 1 --source Request --content '[{"text":{"text":"What stocks should I buy?"}}]' --region us-east-1 output.json
  aws cloudwatch get-metric-statistics --namespace AWS/Bedrock --metric-name GuardrailInvocations --dimensions Name=GuardrailId,Value=abc123def --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Sum --region us-east-1
```

---

## Step 4 — Provisioning commands

```bash
# Create the guardrail with all filter configurations
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail for customer-facing LLM application" \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/abc-123 \
  --content-policy-config '{
    "filtersConfig": [
      {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "VIOLENCE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "HATE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"}
    ]
  }' \
  --topic-policy-config '{
    "topicsConfig": [
      {"name": "Financial_Advice", "definition": "Investment recommendations, stock tips, financial planning", "examples": ["What stocks should I buy?"], "type": "DENY"},
      {"name": "Medical_Diagnosis", "definition": "Medical diagnosis or treatment recommendations", "examples": ["What illness do I have?"], "type": "DENY"}
    ]
  }' \
  --word-policy-config '{
    "managedWordListsConfig": [{"type": "PROFANITY"}],
    "wordsConfig": [{"text": "competitor_a"}, {"text": "competitor_b"}, {"text": "codename_x"}]
  }' \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "BLOCK"},
      {"type": "PHONE", "action": "BLOCK"},
      {"type": "SSN", "action": "BLOCK"},
      {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"}
    ]
  }' \
  --contextual-grounding-policy-config '{
    "filtersConfig": [
      {"type": "GROUNDING", "threshold": 0.75},
      {"type": "RESPONSE_RELEVANCE", "threshold": 0.75}
    ]
  }' \
  --region us-east-1

# Apply to the Bedrock Agent
aws bedrock update-agent \
  --agent-id agt-xyz \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=1 \
  --region us-east-1
```

---

## Step 5 — Post-deployment verification

```bash
# Verify guardrail configuration
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version 1 \
  --region us-east-1

# Verify guardrail applied to Agent
aws bedrock get-agent \
  --agent-id agt-xyz \
  --region us-east-1 \
  --query 'guardrailConfiguration'

# Test with a denied topic (should BLOCK)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version 1 \
  --source Request \
  --content '[{"text":{"text":"What stocks should I buy for maximum profit?"}}]' \
  --region us-east-1 /tmp/topic-block.json

# Test with a legitimate prompt (should ALLOW)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version 1 \
  --source Request \
  --content '[{"text":{"text":"What is the capital of France?"}}]' \
  --region us-east-1 /tmp/legit-pass.json

# Test PII blocking
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version 1 \
  --source Request \
  --content '[{"text":{"text":"My SSN is 123-45-6789"}}]' \
  --region us-east-1 /tmp/pii-block.json
```

---

## Common pitfalls to verify after deployment

1. **Guardrail is applied to the Agent.** A guardrail that is not
   applied filters nothing. Verify with
   `aws bedrock get-agent --query 'guardrailConfiguration'`.

2. **PII filters use BLOCK, not AUDIT.** AUDIT logs but allows the
   response through — PII leaks. Verify action=BLOCK for each PII
   entity with `get-guardrail`.

3. **Content filter severity is not NONE.** NONE means explicitly
   disabled. Verify each category has a real severity level (LOW,
   MEDIUM, or HIGH) for both input and output directions.

4. **Test with ApplyGuardrail before production traffic.** The only
   way to confirm the guardrail actually filters is to send test
   prompts and verify the BLOCK action is returned.
