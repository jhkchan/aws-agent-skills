# End-to-End Example: VPC Lattice Service Deployment

A walkthrough showing how to use the `vpclattice-service-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a VPC Lattice service network with an HTTP service
that uses canary traffic splitting, IAM auth at the service level, and
CloudWatch access logs. The deployment needs:

- Service network: prod-network (auth type AWS_IAM)
- Service: payments-svc (HTTP)
- Target group stable: tg-stable (INSTANCE, port 8080, VPC vpc-aaa11122)
- Target group canary: tg-canary (INSTANCE, port 8080)
- Listener: port 80, HTTP
- Rule: /api/* path routes 20% to canary, 80% to stable
- Auth policy: IAM auth at SERVICE level (covers all rules)
- Access logs: CloudWatch (/aws/vpc-lattice)
- VPC association: vpc-aaa11122

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-vpclattice-service
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a VPC Lattice service network with a payments HTTP
      service. Canary traffic splitting 20/80. IAM auth at the
      service level. CloudWatch access logs. VPC vpc-aaa11122."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a vpc lattice service network"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
VPC_LATTICE: sni-aaa111 → svc-bbb222 (payments-svc-xxx.example.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service network: sni-aaa111 (auth type: AWS_IAM)
  [✓] Target group: tgc-stable (type: INSTANCE, port: 8080)
  [✓] Health check: path /health, interval 30s — targets 3/3 healthy
  [✓] Service: svc-bbb222 (protocol: HTTP, DNS: payments-svc-xxx.example.com)
  [✓] Listener: lstn-ccc333 (port 80, protocol HTTP)
  [✓] Listener rules: 1 rule (path /api/* → canary 20% / stable 80%)
  [✓] Auth policy: IAM auth at SERVICE level (covers ALL rules)
  [✓] VPC association: vpc-aaa11122 associated with sni-aaa111 — ACTIVE
  [✓] Traffic splitting: canary 20% / stable 80%
  [✓] Access logs: CloudWatch (/aws/vpc-lattice)
  [✓] Tags: Environment=production, Topology=canary
VERIFICATION_COMMANDS:
  aws vpc-lattice get-service-network --service-network-identifier sni-aaa111
  aws vpc-lattice get-service --service-identifier svc-bbb222
  aws vpc-lattice list-targets --target-group-identifier tgc-stable
  aws vpc-lattice list-rules --service-identifier svc-bbb222 --listener-identifier lstn-ccc333
```

---

## Step 3 — Provisioning commands

```bash
# 1. Create the service network
SN_ID=$(aws vpc-lattice create-service-network \
  --name prod-network --auth-type AWS_IAM \
  --tags Environment=production \
  --query 'id' --output text)

# 2. Create the stable target group with health check
TG_ID=$(aws vpc-lattice create-target-group \
  --name tg-stable --type INSTANCE \
  --config '{"port":8080,"protocol":"HTTP","vpcIdentifier":"vpc-aaa11122","healthCheck":{"enabled":true,"path":"/health","protocol":"HTTP","intervalSeconds":30,"timeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}}' \
  --query 'id' --output text)

# 3. Register stable targets
aws vpc-lattice register-targets \
  --target-group-identifier "$TG_ID" \
  --targets '[{"id":"i-aaa111222333444","port":8080}]

# 4. Create the canary target group
TG_CANARY_ID=$(aws vpc-lattice create-target-group \
  --name tg-canary --type INSTANCE \
  --config '{"port":8080,"protocol":"HTTP","vpcIdentifier":"vpc-aaa11122","healthCheck":{"enabled":true,"path":"/health","protocol":"HTTP","intervalSeconds":30,"healthyThresholdCount":2}}' \
  --query 'id' --output text)

# 5. Create the service
SVC_ID=$(aws vpc-lattice create-service \
  --name payments-svc \
  --query 'id' --output text)

# 6. Create the listener with default action
LISTENER_ID=$(aws vpc-lattice create-listener \
  --service-identifier "$SVC_ID" \
  --default-action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_ID'","weight":100}]}}' \
  --protocol HTTP --port 80 --name payments-listener \
  --query 'id' --output text)

# 7. Create the canary traffic split rule
aws vpc-lattice create-rule \
  --service-identifier "$SVC_ID" \
  --listener-identifier "$LISTENER_ID" \
  --name canary-split --priority 10 \
  --match '{"httpMatch":{"path":{"prefix":"/api"}}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_CANARY_ID'","weight":20},{"targetGroupIdentifier":"'$TG_ID'","weight":80}]}}]'

# 8. Set auth type and put auth policy
aws vpc-lattice update-service \
  --service-identifier "$SVC_ID" \
  --body '{"authType":"AWS_IAM"}'

aws vpc-lattice put-auth-policy \
  --resource-identifier "$SVC_ID" \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/PaymentsCaller"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*"}]}]

# 9. Associate the VPC with the service network
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SN_ID" \
  --vpc-identifier vpc-aaa11122

# 10. Enable access logs to CloudWatch
aws vpc-lattice put-access-log-subscription \
  --resource-identifier "$SN_ID" \
  --service-network-log-type SERVICE \
  --log-destination '{"provider":"cloudwatch","destinationArn":"arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc-lattice"}'
```

---

## Step 4 — Post-deployment verification

```bash
# Verify service network
aws vpc-lattice get-service-network \
  --service-network-identifier "$SN_ID"

# Verify target health
aws vpc-lattice list-targets \
  --target-group-identifier "$TG_ID" \
  --query 'items[*].{Target:id,Status:status}' --output table

# Verify listener rules
aws vpc-lattice list-rules \
  --service-identifier "$SVC_ID" \
  --listener-identifier "$LISTENER_ID" \
  --query 'items[*].{Name:name,Priority:priority}' --output table

# Verify VPC association status
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SN_ID" \
  --query 'items[*].{VPC:vpcId,Status:status}' --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Auth policy scope | Tries per-rule auth | Auth at SERVICE level (covers all rules) | VPC Lattice auth policy attaches to service, not rules |
| Health checks | Treats as optional monitoring | Health check determines routing eligibility | Unhealthy targets receive ZERO traffic; all unhealthy = 503 |
| VPC association | Forgets to associate VPC | Explicit VPC association with service network | Without association, VPC cannot resolve Lattice DNS |
| Service network | Creates per VPC | Account-level (1 typical); VPCs associated | Service network is the routing plane, not a VPC construct |
| Traffic weights | Assumes must sum to 100 | Weights are relative; Lattice normalizes | Weights 1+4 = same 20/80 as 20+80 |
| Custom domain cert | Requests cert in service region | ACM cert must be in us-east-1 | Lattice-managed TLS region is us-east-1 |

---

## Related artifacts

- **Skill definition:** `skills/vpclattice-service-deployer/SKILL.md`
- **Auth policy and access guide:** `skills/vpclattice-service-deployer/references/auth-policy-and-access.md`
- **Listener rules and health guide:** `skills/vpclattice-service-deployer/references/listener-rules-and-health.md`
- **Slash command:** `commands/aws/deploy-vpclattice-service.md`
- **Eval suite:** `skills/vpclattice-service-deployer/evals/evals.json`
- **Legacy test cases:** `skills/vpclattice-service-deployer/eval/test-cases.yaml`
