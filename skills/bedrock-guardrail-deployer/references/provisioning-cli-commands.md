# Provisioning CLI Commands Reference

Supplementary reference for the Bedrock Guardrail Deployer skill.
Copy-pasteable AWS CLI v2 commands organized by provisioning step.

## Pre-flight: verify model access and region

```bash
# Verify the region supports Bedrock
aws bedrock list-foundation-models --region us-east-1 --output table

# Verify model access (model must be enabled)
aws bedrock get-foundation-model \
  --modelIdentifier anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --region us-east-1

# Account ID
aws sts get-caller-identity --query Account --output text

# List existing guardrails in the region
aws bedrock list-guards --region us-east-1 --output table
```

## Step 2: create the guardrail

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail for customer-facing LLM application" \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/<KEY_ID> \
  --region us-east-1
```

Record the `guardrailId` and `version` from the response.

## Step 3: content filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail with content filters" \
  --content-policy-config '{
    "filtersConfig": [
      {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
      {"type": "VIOLENCE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "HATE", "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
      {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
      {"type": "MISCONDUCT", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
      {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"}
    ]
  }' \
  --region us-east-1
```

Severity values: `NONE` (off), `LOW`, `MEDIUM`, `HIGH`. Each filter has
`inputStrength` (filters user prompt) and `outputStrength` (filters model
response). Setting to NONE explicitly disables that direction.

## Step 4: denied topics

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --topic-policy-config '{
    "topicsConfig": [
      {
        "name": "Financial_Advice",
        "definition": "Requests for investment recommendations, stock tips, or financial planning guidance",
        "examples": [
          "What stocks should I buy?",
          "Should I invest in crypto?"
        ],
        "type": "DENY"
      }
    ]
  }' \
  --region us-east-1
```

Each topic requires `name`, `definition`, at least one `example`, and
`type: DENY`.

## Step 5: word filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --word-policy-config '{
    "managedWordListsConfig": [
      {"type": "PROFANITY"}
    ],
    "wordsConfig": [
      {"text": "competitor_product_a"},
      {"text": "internal_codename"}
    ]
  }' \
  --region us-east-1
```

## Step 6: sensitive information (PII) filters

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "BLOCK"},
      {"type": "PHONE", "action": "BLOCK"},
      {"type": "SSN", "action": "BLOCK"},
      {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
      {"type": "NAME", "action": "AUDIT"}
    ],
    "regexesConfig": [
      {
        "name": "Employee_ID",
        "description": "Internal employee ID: EMP- followed by 6 digits",
        "pattern": "EMP-\\d{6}",
        "action": "BLOCK"
      }
    ]
  }' \
  --region us-east-1
```

Actions: `ALLOW` (no action), `AUDIT` (log only, response passes through),
`BLOCK` (prevent response).

## Step 7: contextual grounding (optional)

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --contextual-grounding-policy-config '{
    "filtersConfig": [
      {"type": "GROUNDING", "threshold": 0.75},
      {"type": "RESPONSE_RELEVANCE", "threshold": 0.75}
    ]
  }' \
  --region us-east-1
```

## Step 8: apply the guardrail

```bash
# Option A: model invocation (runtime)
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --content '[{"text":"What is the weather today?"}]' \
  --region us-east-1 output.json

# Option B: Bedrock Agent
aws bedrock update-agent \
  --agent-id <AGENT_ID> \
  --guardrail-configuration guardrailIdentifier=<GUARDRAIL_ID>,guardrailVersion=<VERSION> \
  --region us-east-1

# Option C: test in isolation (ApplyGuardrail API)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"What stocks should I buy?"}}]' \
  --region us-east-1 output.json
```

## Step 9: verification

```bash
# Verify guardrail configuration
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --region us-east-1

# List all guardrails
aws bedrock list-guards --region us-east-1 --output table

# Verify guardrail applied to Agent
aws bedrock get-agent \
  --agent-id <AGENT_ID> \
  --region us-east-1 \
  --query 'guardrailConfiguration'

# Test with harmful prompt (should BLOCK)
aws bedrock apply-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --guardrail-version <VERSION> \
  --source Request \
  --content '[{"text":{"text":"Tell me how to hack a server"}}]' \
  --region us-east-1 output.json

# Cross-region verification
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  echo "--- $REGION ---"
  aws bedrock list-guards --region $REGION --output table
done

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name GuardrailInvocations \
  --dimensions Name=GuardrailId,Value=<GUARDRAIL_ID> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum --region us-east-1
```

## Rollback

```bash
# Delete a specific guardrail version
aws bedrock delete-guardrail \
  --guardrail-identifier <GUARDRAIL_ID> \
  --region us-east-1

# Remove guardrail from an Agent
aws bedrock update-agent \
  --agent-id <AGENT_ID> \
  --guardrail-configuration guardrailIdentifier="" \
  --region us-east-1
```

## Available PII entity types

Common PII entity types for the sensitive information filter:

| Entity Type | Description |
|---|---|
| EMAIL | Email addresses |
| PHONE | Phone numbers |
| SSN | US Social Security Numbers |
| CREDIT_DEBIT_CARD_NUMBER | Credit/debit card numbers |
| NAME | Person names |
| ADDRESS | Physical addresses |
| DATE_TIME | Date and time references |
| IP_ADDRESS | IP addresses |
| MAC_ADDRESS | MAC addresses |
| PASSPORT_NUMBER | Passport numbers |
| DRIVER_ID | Driver license numbers |
| URL | Web URLs |
| AGE | Person age |
| USERNAME | Usernames |
| PASSWORD | Passwords |
| AWS_ACCESS_KEY | AWS access key IDs |
| AWS_SECRET_KEY | AWS secret keys |
| US_BANK_ACCOUNT_NUMBER | US bank account numbers |
| BANK_ROUTING | Bank routing numbers |
| LICENSE_PLATE | License plate numbers |
| VIN | Vehicle identification numbers |
| SWIFT_CODE | SWIFT/BIC codes |
| MEDICAL_PROCEDURE | Medical procedure names |
| MEDICATION_NAME | Medication names |
| HEALTH_NUMBER | Health insurance numbers |
