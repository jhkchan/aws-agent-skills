# End-to-End Example: Global Accelerator Deployment

A walkthrough showing how to use the `global-accelerator-endpoint-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a multi-region Global Accelerator with active-
passive failover between an ALB in us-east-1 (primary) and an ALB in
us-west-2 (DR). The accelerator needs:

- Two static anycast IP addresses (auto-assigned)
- TCP listener on ports 80 and 443
- Primary: us-east-1, traffic dial 1.0, ALB endpoint
- DR: us-west-2, traffic dial 0.0, ALB endpoint
- Health check: HTTPS /health port 443, 10-second interval
- Client IP preservation: enabled
- Flow logs to CloudWatch

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-global-accelerator-endpoint
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Global Accelerator with active-passive failover.
      Primary us-east-1 traffic dial 1.0, DR us-west-2 traffic
      dial 0.0. ALB endpoints. Listener TCP 443."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a global accelerator"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
GLOBAL_ACCELERATOR: prod-accelerator (arn:aws:globalaccelerator::123456789012:accelerator/abcd1234)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Accelerator: prod-accelerator — ENABLED
  [✓] Anycast IPs: 192.0.2.1, 192.0.2.2 — PINNED at creation
  [✓] Listener: TCP ports 80, 443 — client affinity NONE
  [✓] Endpoint group (us-east-1): traffic dial 1.0, health 10s/HTTPS//health
  [✓] Endpoint group (us-west-2): traffic dial 0.0, health 10s/HTTPS//health
  [✓] Endpoints: ALB weight 128 each
  [✓] Client IP preservation: ENABLED
  [✓] Flow logs: /aws/globalaccelerator/prod
  [✓] Failover strategy: Active-passive
VERIFICATION_COMMANDS:
  aws globalaccelerator describe-accelerator --accelerator-arn <arn>
  aws globalaccelerator list-listeners --accelerator-arn <arn>
  aws globalaccelerator list-endpoint-groups --listener-arn <arn>
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the accelerator (anycast IPs pinned at creation)
ACCEL_ARN=$(aws globalaccelerator create-accelerator \
  --name "prod-accelerator" \
  --ip-address-type IPV4 \
  --enabled \
  --query 'Accelerator.AcceleratorArn' --output text)

# Step 2: Create listener (TCP 80, 443)
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --accelerator-arn "$ACCEL_ARN" \
  --protocol TCP \
  --port-ranges FromPort=80,ToPort=80 FromPort=443,ToPort=443 \
  --client-affinity NONE \
  --query 'Listener.ListenerArn' --output text)

# Step 3: Create endpoint group — primary (us-east-1, dial 1.0)
EG_PRIMARY=$(aws globalaccelerator create-endpoint-group \
  --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region us-east-1 \
  --traffic-dial 1.0 \
  --health-check-interval-seconds 10 \
  --health-check-path /health \
  --health-check-port 443 \
  --health-check-protocol HTTPS \
  --threshold-count 3 \
  --query 'EndpointGroup.EndpointGroupArn' --output text)

# Step 4: Create endpoint group — DR (us-west-2, dial 0.0)
EG_DR=$(aws globalaccelerator create-endpoint-group \
  --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region us-west-2 \
  --traffic-dial 0.0 \
  --health-check-interval-seconds 10 \
  --health-check-path /health \
  --health-check-port 443 \
  --health-check-protocol HTTPS \
  --threshold-count 3 \
  --query 'EndpointGroup.EndpointGroupArn' --output text)

# Step 5: Add ALB endpoint to primary group
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/prod-alb-east/abc123,Weight=128

# Step 6: Add ALB endpoint to DR group
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_DR" \
  --endpoint-configurations \
    EndpointId=arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/prod-alb-west/def456,Weight=128
```

---

## Step 4 — Post-deployment verification

```bash
# Accelerator status — should be ENABLED
aws globalaccelerator describe-accelerator \
  --accelerator-arn "$ACCEL_ARN" \
  --query 'Accelerator.{Name:Name,Status:Status,Ips:IpSets[0].IpAddresses}'

# Listeners — verify port ranges
aws globalaccelerator list-listeners \
  --accelerator-arn "$ACCEL_ARN"

# Endpoint groups — verify traffic dial
aws globalaccelerator list-endpoint-groups \
  --listener-arn "$LISTENER_ARN" \
  --query 'EndpointGroups[*].{Region:EndpointGroupRegion,Dial:TrafficDialPercentage}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Anycast IPs | Not flagged as pinned | Explicitly noted as PINNED at creation | Cannot be changed without recreating accelerator |
| Traffic dial | Confused with weight | Traffic dial (regions) vs endpoint weight (within region) | Different control layers |
| Health checks | Assumed same as target group | Independent health checks noted | GA health checks are separate from ALB/NLB target group |
| BYOIP | Added after creation | Must precede accelerator creation | Pool must be READY before accelerator |
| Failover | Not planned | Active-passive strategy with dial 0.0 for DR | DR must have healthy endpoints for failover |

---

## Related artifacts

- **Skill definition:** `skills/global-accelerator-endpoint-deployer/SKILL.md`
- **Anycast and traffic dial guide:** `skills/global-accelerator-endpoint-deployer/references/anycast-and-traffic-dial.md`
- **Endpoint types and failover guide:** `skills/global-accelerator-endpoint-deployer/references/endpoint-types-and-failover.md`
- **Slash command:** `commands/aws/deploy-global-accelerator-endpoint.md`
- **Eval suite:** `skills/global-accelerator-endpoint-deployer/evals/evals.json`
- **Legacy test cases:** `skills/global-accelerator-endpoint-deployer/eval/test-cases.yaml`
