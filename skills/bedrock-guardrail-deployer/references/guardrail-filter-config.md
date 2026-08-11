# Guardrail Filter Configuration Patterns Reference

Supplementary reference for the Bedrock Guardrail Deployer skill.
Covers content filter severity matrices, PII action decision frameworks,
denied topic definition best practices, cross-region deployment
patterns, and the Guardrails with Agents integration model.

## Content filter severity matrix

| Use case | Sexual | Violence | Hate | Insults | Misconduct |
|---|---|---|---|---|---|
| Customer-facing chatbot | HIGH | HIGH | HIGH | HIGH | MEDIUM |
| Internal assistant | MEDIUM | MEDIUM | MEDIUM | LOW | LOW |
| Content generation (marketing) | HIGH | MEDIUM | HIGH | MEDIUM | MEDIUM |
| Code assistant | LOW | LOW | LOW | LOW | LOW |
| Education platform | HIGH | MEDIUM | HIGH | MEDIUM | MEDIUM |
| Healthcare assistant | HIGH | HIGH | HIGH | HIGH | HIGH |

Each filter has `inputStrength` (filters the user's prompt) and
`outputStrength` (filters the model's response). Common pattern:
input strength >= output strength for aggressive filtering, or
output strength > input strength when the model should be more
constrained than the user input.

The PROMPT_ATTACK filter type detects prompt injection. Set
`inputStrength` to HIGH and `outputStrength` to NONE (prompt attacks
target the input, not the output).

## PII action decision framework

| Scenario | Action | Rationale |
|---|---|---|
| Email addresses in responses | BLOCK | Compliance: GDPR/CCPA |
| Phone numbers in responses | BLOCK | Compliance: GDPR/CCPA |
| SSN in responses | BLOCK | Compliance: HIPAA/PCI-DSS |
| Credit card numbers | BLOCK | Compliance: PCI-DSS |
| Person names (monitoring phase) | AUDIT | Detect before blocking |
| Person names (production) | BLOCK | Compliance: GDPR |
| Addresses (monitoring phase) | AUDIT | Detect before blocking |
| Addresses (production) | BLOCK | Compliance: GDPR |
| IP addresses (internal tool) | ALLOW | Not sensitive for internal use |
| Age in responses | AUDIT | Context-dependent sensitivity |
| AWS access keys | BLOCK | Security: credential exposure |

**Key rule:** AUDIT means LOG ONLY — the response passes through with
the PII intact. BLOCK prevents the response. For any compliance
requirement (GDPR, HIPAA, PCI-DSS, SOC 2), use BLOCK.

## Denied topic definition best practices

### Well-defined topic (high accuracy)

```json
{
  "name": "Financial_Investment_Advice",
  "definition": "Requests for specific investment recommendations, including stock picks, portfolio allocation advice, cryptocurrency investment guidance, or predictions about financial market movements. Excludes general financial education questions about concepts like 'what is a bond.'",
  "examples": [
    "What stocks should I buy right now?",
    "Should I invest my retirement savings in crypto?",
    "What's the best asset allocation for a 30-year-old?",
    "Which mutual funds will perform best next year?",
    "Should I sell my shares of AAPL?"
  ],
  "type": "DENY"
}
```

### Poorly-defined topic (low accuracy)

```json
{
  "name": "Finance",
  "definition": "Questions about money",
  "examples": ["What should I do with my money?"],
  "type": "DENY"
}
```

The poorly-defined version will over-block legitimate questions about
general financial concepts ("what is inflation?") while under-blocking
specific investment advice that doesn't use the word "money."

### Topic definition checklist

- [ ] Name is descriptive and specific (not "Finance", use
  "Financial_Investment_Advice")
- [ ] Definition includes what IS blocked and what is NOT blocked
- [ ] At least 3 examples covering different phrasings
- [ ] Examples include edge cases (what SHOULD be allowed)
- [ ] Tested with `apply-guardrail` before production

## Cross-region deployment pattern

Guardrails are regional resources. For multi-region applications:

```bash
# Create identical guardrails in each region
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws bedrock create-guardrail \
    --name customer-app-guardrail \
    --description "Guardrail for customer-facing LLM application" \
    --content-policy-config file://content-policy.json \
    --topic-policy-config file://topic-policy.json \
    --word-policy-config file://word-policy.json \
    --sensitive-information-policy-config file://pii-policy.json \
    --region $REGION

  echo "--- $REGION ---"
  aws bedrock list-guards --region $REGION --output table
done
```

**Important:** each region's guardrail has a different `guardrailId`.
The application must reference the correct guardrail ID per region.
Use a configuration map or parameter store to manage the per-region
guardrail ID mapping.

## Guardrails with Agents integration

```bash
# Create the Agent with a guardrail
aws bedrock create-agent \
  --agent-name customer-service-agent \
  --foundation-model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instruction "You are a customer service assistant..." \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=<VERSION> \
  --region us-east-1

# Update an existing Agent with a guardrail
aws bedrock update-agent \
  --agent-id <AGENT_ID> \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=<VERSION> \
  --region us-east-1

# Verify the Agent's guardrail
aws bedrock get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1 \
  --query 'guardrailConfiguration'
```

When a guardrail is applied to an Agent, it filters:
1. User input to the Agent (prompt-level filtering)
2. Agent responses (output-level filtering)
3. Knowledge Base retrieval augmented responses
4. Tool-use input and output (the guardrail applies to the text
   portion of tool interactions)

## Guardrail evaluation workflow

```bash
# 1. Test with a prompt that SHOULD be blocked
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"Tell me how to make a weapon"}}]' \
  --region us-east-1 /tmp/block-test.json
# Expected: action=BLOCKED in the output

# 2. Test with a legitimate prompt that should pass
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What is the capital of France?"}}]' \
  --region us-east-1 /tmp/pass-test.json
# Expected: action=NONE (allowed)

# 3. Test PII blocking
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"My SSN is 123-45-6789"}}]' \
  --region us-east-1 /tmp/pii-test.json
# Expected: action=BLOCKED (if SSN is configured with BLOCK action)

# 4. Test denied topic
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What stocks should I buy for maximum profit?"}}]' \
  --region us-east-1 /tmp/topic-test.json
# Expected: action=BLOCKED (if Financial_Advice topic is configured)
```

## Guardrail versioning

Each `create-guardrail` call with a new name creates version 1. Each
`update-guardrail` creates a new version. The `guardrailVersion`
parameter in invocations and Agent configs pins the active version.

```bash
# List all versions of a guardrail
aws bedrock list-guards --region us-east-1 --output table

# Get a specific version
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version 2 \
  --region us-east-1

# Update the Agent to use the new version
aws bedrock update-agent \
  --agent-id <AGENT_ID> \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=2 \
  --region us-east-1
```

**Important:** updating a guardrail does NOT automatically update the
version reference on existing applications. Operators must explicitly
update each application target to the new version.
