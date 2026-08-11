# Anycast IPs and Traffic Dial — Global Accelerator Endpoint Deployer

Deep reference on anycast IP address mechanics (pinned at creation,
BYOIP prerequisites), traffic dial behavior (normalized percentages,
regional canary), endpoint weight semantics (0-255 within a group),
and the interaction between the three traffic control layers. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Anycast IP address fundamentals

### How anycast works in Global Accelerator

Anycast means the same IP address is advertised from multiple AWS edge
locations worldwide. When a client connects, the BGP routing protocol
directs the traffic to the nearest edge location. From there, traffic
traverses the AWS global backbone to the target region.

```text
Client (Tokyo) → nearest edge (Tokyo) → AWS backbone → endpoint (us-east-1)
Client (London) → nearest edge (London) → AWS backbone → endpoint (us-east-1)
Client (New York) → nearest edge (NYC) → AWS backbone → endpoint (us-east-1)
```

Both anycast IPs map to the same accelerator. DNS resolves both IPs
globally, and the routing protocol handles proximity.

### Why anycast IPs are pinned at creation

The two static anycast IP addresses are allocated from AWS's anycast IP
pool (or from your BYOIP pool) when the accelerator is created. They
are associated with the accelerator's ARN permanently. There is no API
to change the IPs without deleting and recreating the accelerator.

This means:
- DNS records pointing to the anycast IPs must be updated when the
  accelerator is recreated.
- BYOIP must be decided BEFORE accelerator creation.
- Blue-green deployments of accelerators require DNS cutover planning.

### BYOIP integration

BYOIP allows using your own IP ranges as anycast IPs:

1. The IP range must be registered with an RIR (ARIN, RIPE, APNIC).
2. A Route Origin Authorization (ROA) must be published by the RIR.
3. Provision the CIDR in AWS: `aws ec2 provision-byoipcidr`.
4. Wait for READY state (ROA propagation, can take 24-48 hours).
5. Advertise: `aws ec2 advertise-byoipcidr`.
6. Create the accelerator referencing the BYOIP pool.

**Verify BYOIP state:**

```bash
aws ec2 describe-byoipcidrs \
  --query 'ByoipCidrs[*].{Cidr:Cidr,State:State}' --output table
```

The state must be `provisioned` and the status `advertised` before
referencing it in a Global Accelerator.

## Traffic dial mechanics

### Normalized percentages

Traffic dial values (0.0 to 1.0) are normalized across all endpoint
groups within a listener. For example:

```text
Endpoint group us-east-1: traffic dial = 0.9
Endpoint group eu-west-1: traffic dial = 0.1
Normalized: us-east-1 = 90%, eu-west-1 = 10%

Endpoint group us-east-1: traffic dial = 1.0
Endpoint group us-west-2: traffic dial = 1.0
Normalized: us-east-1 = 50%, us-west-2 = 50%

Endpoint group us-east-1: traffic dial = 1.0
Endpoint group us-west-2: traffic dial = 0.0
Normalized: us-east-1 = 100%, us-west-2 = 0% (drained)
```

### Regional canary deployment

Traffic dial enables canary deployments at the regional level:

```bash
# Start: 100% us-east-1, 0% eu-west-1
# Canary: shift 10% to eu-west-1
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_EU_WEST" \
  --traffic-dial 0.1

# Verify traffic split
aws globalaccelerator describe-endpoint-group \
  --endpoint-group-arn "$EG_EU_WEST" \
  --query 'EndpointGroup.TrafficDialPercentage'
```

### Drain a region

Setting traffic dial to 0.0 drains the region. Existing flows may
continue until they naturally end, but no new flows are sent.

## Endpoint weight semantics

### Weight calculation within a group

Endpoint weights (0-255) determine traffic distribution WITHIN a single
endpoint group. The share of traffic for each endpoint is:

```
endpoint_share = endpoint_weight / sum(all_endpoint_weights)
```

```text
Endpoint A: weight 128
Endpoint B: weight 128
Result: 50/50 split

Endpoint A: weight 255
Endpoint B: weight 128
Result: ~67/33 split

Endpoint A: weight 0 (drained)
Endpoint B: weight 128
Result: 100% to B
```

### Draining individual endpoints

Setting an endpoint's weight to 0 drains it without removing it from
the endpoint group. This is useful for maintenance:

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=arn:...:loadbalancer/app/my-alb/abc123,Weight=0
```

## Interaction between traffic dial and endpoint weight

The three layers operate independently:

1. Anycast IPs route to the nearest AWS edge (fixed at creation).
2. Traffic dial routes between endpoint groups (regions).
3. Endpoint weight routes between endpoints within a group.

```text
Client → Anycast IP → nearest edge → AWS backbone
  → Traffic dial determines which region
    → Endpoint weight determines which endpoint in that region
```

## Terraform examples

```hcl
resource "aws_globalaccelerator_accelerator" "main" {
  name            = "prod-accelerator"
  ip_address_type = "IPV4"
  enabled         = true

  attributes {
    flow_logs_enabled             = true
    flow_logs_s3_bucket           = aws_s3_bucket.ga_logs.bucket
    flow_logs_s3_prefix           = "ga-flow-logs/"
  }
}

resource "aws_globalaccelerator_listener" "https" {
  accelerator_arn = aws_globalaccelerator_accelerator.main.id
  protocol        = "TCP"
  client_affinity = "NONE"

  port_range {
    from_port = 443
    to_port   = 443
  }
}

resource "aws_globalaccelerator_endpoint_group" "primary" {
  listener_arn              = aws_globalaccelerator_listener.https.id
  endpoint_group_region     = "us-east-1"
  traffic_dial_percentage   = 100  # 1.0 in CLI = 100 in TF
  health_check_interval_seconds = 10
  health_check_path             = "/health"
  health_check_port             = 443
  health_check_protocol         = "HTTPS"
  threshold_count               = 3

  endpoint_configuration {
    endpoint_id = aws_lb.primary_alb.arn
    weight      = 128
  }
}

resource "aws_globalaccelerator_endpoint_group" "dr" {
  listener_arn              = aws_globalaccelerator_listener.https.id
  endpoint_group_region     = "us-west-2"
  traffic_dial_percentage   = 0
  health_check_interval_seconds = 10
  health_check_path             = "/health"
  health_check_port             = 443
  health_check_protocol         = "HTTPS"
  threshold_count               = 3

  endpoint_configuration {
    endpoint_id = aws_lb.dr_alb.arn
    weight      = 128
  }
}
```
