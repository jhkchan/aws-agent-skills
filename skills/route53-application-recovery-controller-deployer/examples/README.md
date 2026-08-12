# End-to-End Example: Route 53 ARC Deployment

A walkthrough showing how to use the
`route53-application-recovery-controller-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an active-standby ARC setup for a multi-region
application with two cells, an OR safety rule, readiness checks, and
Route 53 health check integration. The setup needs:

- Recovery cluster: app-recovery-cluster
- Cell-A: us-east-1 (primary, NLB + ASG)
- Cell-B: us-west-2 (standby, NLB + ASG)
- Safety rule: OR threshold 1 (prevent total outage)
- Topology: Active-Standby
- Tags: Environment=production, Application=app

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-route53-arc
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Route 53 ARC setup for my application. Two cells:
      Cell-A in us-east-1 and Cell-B in us-west-2. Active-standby
      with Cell-A primary. Need safety rule to prevent total
      outage. Readiness checks for NLB and ASG."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create route 53 arc"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ARC: app-recovery-cluster (arn:aws:route53-recovery-control-config:us-east-1:123456789012:cluster/abc123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Recovery cluster: app-recovery-cluster — ACTIVE
  [✓] Cells: Cell-A (us-east-1), Cell-B (us-west-2)
  [✓] Resource sets: app-nlb (AWS::ElasticLoadBalancingV2::LoadBalancer), app-asg (AWS::AutoScaling::AutoScalingGroup)
  [✓] Control panel: app-failover-control-panel
  [✓] Routing controls: cell-a-traffic, cell-b-traffic
  [✓] Safety rule: prevent-total-outage (OR, threshold 1) — prevents total outage
  [✓] Readiness checks: app-nlb-check, app-asg-check
  [✓] Cross-region readiness: READY
  [✓] Topology: Active-Standby (Cell-A primary)
  [✓] CloudWatch alarm: arc-routing-control-changed for cell-a-traffic
  [✓] Tags: Environment=production, Application=app
VERIFICATION_COMMANDS:
  aws route53-recovery-control-config describe-cluster --cluster-arn <cluster-arn>
  aws route53-recovery-cluster get-routing-control-state --routing-control-arn <rc-arn>
  aws route53-recovery-readiness get-cell-readiness --cell-name Cell-B
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the recovery cluster (~10-15 minutes)
CLUSTER_ARN=$(aws route53-recovery-control-config create-cluster \
  --cluster-name "app-recovery-cluster" \
  --query 'Cluster.ClusterArn' --output text)

# Step 2: Create control panel
aws route53-recovery-control-config create-control-panel \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel"

# Step 3: Create routing controls (one per cell)
RC_A_ARN=$(aws route53-recovery-control-config create-routing-control \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel" \
  --routing-control-name "cell-a-traffic" \
  --query 'RoutingControl.RoutingControlArn' --output text)

RC_B_ARN=$(aws route53-recovery-control-config create-routing-control \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel" \
  --routing-control-name "cell-b-traffic" \
  --query 'RoutingControl.RoutingControlArn' --output text)

# Step 4: Create safety rule (OR, threshold 1 — prevent total outage)
aws route53-recovery-control-config create-safety-rule \
  --control-panel-name "app-failover-control-panel" \
  --safety-rule-name "prevent-total-outage" \
  --rule-config '{"Type":"OR","Inverted":false,"Threshold":1}' \
  --routing-controls-arns "$RC_A_ARN" "$RC_B_ARN"

# Step 5: Create resource sets and readiness checks
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-nlb-rs" \
  --resource-set-type "AWS::ElasticLoadBalancingV2::LoadBalancer" \
  --resources '[...]'

aws route53-recovery-readiness create-readiness-check \
  --readiness-check-name "app-nlb-check" \
  --resource-set-name "app-nlb-rs"

# Step 6: Toggle Cell-A routing control ON (Cell-A is primary)
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_A_ARN" \
  --routing-control-state "On"
```

---

## Step 4 — Post-deployment verification

```bash
# Cluster status
aws route53-recovery-control-config describe-cluster \
  --cluster-arn "$CLUSTER_ARN"

# Routing control states
aws route53-recovery-cluster get-routing-control-state \
  --routing-control-arn "$RC_A_ARN"
aws route53-recovery-cluster get-routing-control-state \
  --routing-control-arn "$RC_B_ARN"

# Cell-B readiness (for failover readiness)
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Safety rules | Not created | OR rule with threshold | Without safety rules, all controls can be OFF simultaneously |
| Config vs cluster API | Uses one API for all | Config for create, cluster for toggle | State toggles go through the quorum data plane |
| Resource type mapping | Generic type strings | Exact CloudFormation types | Readiness templates match by full type |
| Readiness checks | Not created | Per resource set | Pre-failover validation catches missing resources |
| OR threshold design | Default to 1 | Topology-aware (1 for standby, 2+ for active-active) | Active-active needs higher threshold |

---

## Related artifacts

- **Skill definition:** `skills/route53-application-recovery-controller-deployer/SKILL.md`
- **Routing controls and safety guide:** `skills/route53-application-recovery-controller-deployer/references/routing-controls-and-safety.md`
- **Readiness and resource sets guide:** `skills/route53-application-recovery-controller-deployer/references/readiness-and-resource-sets.md`
- **Slash command:** `commands/aws/deploy-route53-arc.md`
- **Eval suite:** `skills/route53-application-recovery-controller-deployer/evals/evals.json`
- **Legacy test cases:** `skills/route53-application-recovery-controller-deployer/eval/test-cases.yaml`
