# End-to-end usage scenario: globalaccelerator-deployer

A walkthrough showing the skill producing a deployment plan for a
production multi-region Global Accelerator with active-active ALB
endpoints, Amazon-pool anycast IPs, S3 flow logs, and X-Forwarded-For
client IP propagation. Demonstrates the READY_TO_DEPLOY verdict,
architecture checklist, and ordered deploy-command list.

## Input (user prompt)

> Provision a Global Accelerator for our multi-region SaaS frontend.
> We have ALBs in us-east-1 and eu-west-1, both serving HTTPS on 443.
> We want active-active traffic (closest region wins), TCP 443 listener,
> flow logs to our S3 bucket `prod-ga-flowlogs`. No BYOIP. The S3
> bucket policy is already configured to grant s3:PutObject to the GA
> logging principal.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — endpoint ARNs
   resolve and match endpoint-group regions, listener protocol and
   port range valid, flow log S3 bucket policy verified, IAM
   permissions confirmed. No BYOIP, no cross-account, no custom
   routing.
2. **Endpoint homogeneity:** Verifies both endpoints are ALB (no
   mixing with NLB or EC2 in the same group). PASS.
3. **Traffic steering:** Active-active via traffic dial 100 in both
   endpoint groups. GA anycast routes each user to the closest region.
4. **Client IP:** ALB endpoints — client IP always reaches origin via
   `X-Forwarded-For`. Application must read the header.
5. **Verdict:** READY_TO_DEPLOY — all checklist dimensions pass.

## Expected output

```text
ACCELERATOR: prod-ga-multi-region
VERDICT: READY_TO_DEPLOY
TARGET: prod-ga-multi-region
PRE_CHECKS:
  - [PASS] Accelerator region us-west-2 valid (control-plane only)
  - [PASS] Amazon pool IP source (no BYOIP provisioning required)
  - [PASS] Listener TCP 443 affinity NONE (stateless HTTPS)
  - [PASS] Endpoint group us-east-1 region matches ALB ARN region
  - [PASS] Endpoint group eu-west-1 region matches ALB ARN region
  - [PASS] Endpoint types homogeneous within each group (ALB only)
  - [PASS] ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc resolves state=active
  - [PASS] ALB arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/app/prod-euw1/def resolves state=active
  - [PASS] Traffic dial 100 in both regions (active-active)
  - [PASS] Health check HTTPS / 30s / threshold 3 matches ALB target group
  - [PASS] Flow log S3 bucket policy grants s3:PutObject to flowlogs.globalaccelerator.amazonaws.com
  - [PASS] IAM principal holds globalaccelerator:CreateAccelerator, CreateListener, CreateEndpointGroup, AddEndpoints
STEPS:
  1. CONFIRM: About to create-accelerator prod-ga-multi-region in account 111111111111. Allocates 2 anycast IPs, TCP/443 listener, 2 endpoint groups (us-east-1 + eu-west-1), 2 ALB endpoints, S3 flow logs. Estimated cost: $18/mo fixed + $0.02/GB ingress. Proceed? (yes/no)
  2. aws globalaccelerator create-accelerator --name prod-ga-multi-region --ip-addresses IPV4 --idempotency-token "$(uuidgen)"
  3. aws globalaccelerator create-listener --accelerator-arn <arn> --protocol TCP --port-ranges FromPort=443,ToPort=443 --client-affinity NONE --region us-west-2
  4. aws globalaccelerator create-endpoint-group --listener-arn <arn> --endpoint-group-region us-east-1 --traffic-dial 100.0 --health-check-interval-seconds 30 --health-check-path / --health-check-port 443 --health-check-protocol HTTPS --threshold-count 3 --region us-west-2
  5. aws globalaccelerator add-endpoints --endpoint-group-arn <arn> --endpoint-configurations '[{"EndpointId":"arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc","Weight":128}]' --region us-west-2
  6. aws globalaccelerator create-endpoint-group --listener-arn <arn> --endpoint-group-region eu-west-1 --traffic-dial 100.0 --health-check-interval-seconds 30 --health-check-path / --health-check-port 443 --health-check-protocol HTTPS --threshold-count 3 --region us-west-2
  7. aws globalaccelerator add-endpoints --endpoint-group-arn <arn> --endpoint-configurations '[{"EndpointId":"arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/app/prod-euw1/def","Weight":128}]' --region us-west-2
  8. aws globalaccelerator update-accelerator-attributes --accelerator-arn <arn> --flow-logs-s3-bucket prod-ga-flowlogs --region us-west-2
POST_VERIFY:
  - (pending execution)
  - describe-accelerator returns Status=DEPLOYED
  - list-endpoint-groups returns 2 groups (us-east-1 + eu-west-1), both traffic-dial=100
  - S3 bucket prod-ga-flowlogs receives flow log objects within 5 minutes of test traffic
IP_SOURCE: Amazon pool (2 anycast IPs)
LISTENER: TCP 443-443 affinity NONE
ENDPOINT_GROUPS: 2 regions us-east-1, eu-west-1
ENDPOINTS: 2 type ALB preservation X-Forwarded-For
FLOW_LOGS: S3 bucket prod-ga-flowlogs
NOTES:
  - Active-active: each user routes to the closest region. Per-endpoint health check fails over within 30 sec.
  - Client IP at origin: ALB reads X-Forwarded-For (not the L4 socket source).
  - Cost: ~$18/mo fixed + $0.02/GB. 1 TB/mo ingress ~= $38/month.
  - DNS: map app.example.com A+AAAA to the 2 anycast IPs returned by describe-accelerator.
```

## What the baseline (no-skill) response misses

A generic assistant without this skill would:
- Not enumerate the 12 pre-check dimensions (anycast IP source,
  endpoint homogeneity, region matching, health check protocol
  match, flow log destination permission, IAM permissions, etc.).
- Not surface the traffic-dial-vs-endpoint-weight distinction
  (per-region vs per-endpoint load balancing).
- Not flag the `X-Forwarded-For` application-code requirement
  (reading the L4 socket source returns the AWS GA IP).
- Not include the CONFIRM gate with cost estimate.
- Not produce a deterministic VERDICT block for downstream
  automation.

The skill converts an open-ended "set up Global Accelerator" prompt
into a deterministic, pre-checked, ordered deploy plan with a single
READY_TO_DEPLOY or PREREQUISITES_MISSING verdict.
