# Route Tables, Associations, and Propagations Reference

Supplementary reference for the Transit Gateway Deployer skill. Use
when designing TGW route table topology, association/propagation
matrices, static routes, blackholes, or segmentation tiers.

## Association vs. propagation — the canonical mental model

| Operation | What it does | Cardinality | CLI |
|---|---|---|---|
| Association | Which route table an attachment LOOKS UP routes in | One per attachment (default + extras allowed) | `associate-transit-gateway-route-table` |
| Propagation | Which route tables an attachment INJECTS its routes into | Many per attachment | `enable-transit-gateway-route-table-propagation` |

A VPC attachment can be associated with one route table (for its
own outbound lookups) and propagate to many route tables (to publish
its routes). Misunderstanding this distinction is the #1 cause of
"VPC attached but unreachable" outages.

## Default route table behavior

At `create-transit-gateway`, two flags control auto-wiring:

| Flag | Effect when `enable` | Effect when `disable` |
|---|---|---|
| `DefaultRouteTableAssociation` | New attachments auto-associate to the default route table | Owner must explicitly associate |
| `DefaultRouteTablePropagation` | New attachments auto-propagate to the default route table | Owner must explicitly propagate |

For simple topologies (1 route table, all VPCs can route to each
other), set both `enable`. For multi-tier segmentation, set both
`disable` and manage route tables explicitly.

The default route table (`DefaultRouteTableId`) is created
automatically with the TGW and CANNOT be deleted. It can be renamed
or repurposed (e.g., as a "reject-all" sink for unknown attachments).

## Static routes and blackholes

```bash
# Static route (CIDR → attachment)
aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id tgw-rtb-0prod \
  --destination-cidr-block 10.20.0.0/16 \
  --transit-gateway-attachment-id tgw-attach-0firewall

# Blackhole (drop traffic to CIDR)
aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id tgw-rtb-0prod \
  --destination-cidr-block 10.99.0.0/16 \
  --blackhole
```

Use cases:
- Default route `0.0.0.0/0` to a firewall/NAT NVA attachment for
  centralized egress.
- Blackhole CIDRs for compliance isolation (PCI scope, DMZ).
- Summary routes pointing to a peering attachment for inter-region
  traffic.
- Blackhole for quarantined VPCs (security incident response).

## Segmentation tier patterns

### Single-tier (flat)

```
TGW
  └─ default route table (auto-association + auto-propagation)
       ├─ vpc-app1 (associated + propagating)
       ├─ vpc-app2 (associated + propagating)
       └─ vpc-shared (associated + propagating)
```

All VPCs can route to each other. Use for under 5 VPCs with no
isolation requirements.

### Two-tier (prod + non-prod)

```
TGW
  ├─ prod-rtb
  │    ├─ vpc-app1-prod (associated + propagating)
  │    └─ vpc-shared (propagating, NOT associated)
  ├─ nonprod-rtb
  │    ├─ vpc-app1-nonprod (associated + propagating)
  │    └─ vpc-shared (propagating, NOT associated)
  └─ default-rtb (reject-all sink)
```

Shared propagates to BOTH prod and non-prod (shared reaches
everyone). Prod does NOT propagate to non-prod (isolation). Use for
dev/prod split.

### Three-tier with centralized egress

```
TGW
  ├─ prod-rtb
  │    ├─ vpc-app1-prod (associated + propagating)
  │    ├─ static route 0.0.0.0/0 → tgw-attach-0firewall
  │    └─ vpc-firewall (propagating)
  ├─ nonprod-rtb
  │    └─ (mirror of prod)
  └─ shared-rtb
       └─ vpc-shared (associated + propagating)
```

All internet-bound traffic hairpins through the firewall VPC
attachment (with appliance mode enabled). Use for centralized
inspection and egress.

## Appliance mode deep-dive

When a VPC attachment has `ApplianceModeSupport=enable`:

- The TGW preserves the source AZ for return traffic.
- Stateful firewalls see symmetric flows (in and out via the same
  AZ's ENI).
- Without appliance mode, return traffic may exit a different AZ's
  ENI, breaking stateful inspection.

Appliance mode is REQUIRED for:
- Centralized firewall topologies (firewall VPC attachment
  inspects all east-west traffic).
- Centralized internet egress via a NAT Gateway or NAT instance.
- Any topology where asymmetric flow handling breaks the
  middlebox.

Appliance mode is per-attachment, set at
`create-transit-gateway-vpc-attachment` time.

## Inter-region peering routing

A peering attachment lands in both TGWs. Each TGW must add the
peering's routes to its route tables. The most common failure mode
is asymmetric routing: TGW A propagates the peering to its route
tables (so A's VPCs can reach B's VPCs), but TGW B does NOT
propagate (so B's VPCs cannot reply).

**Fix:** explicitly enable propagation on BOTH TGWs. Verify with:

```bash
aws ec2 get-transit-gateway-route-table-associations \
  --transit-gateway-route-table-id <rtb-id>
aws ec2 get-transit-gateway-route-table-propagations \
  --transit-gateway-route-table-id <rtb-id>
```

## Connect attachment routing

BGP routes advertised by the Connect peer (your SD-WAN controller)
land in the Connect attachment's route table as propagated routes.
The TGW installs them as routes pointing at the Connect attachment,
so VPCs with routes to the Connect attachment can reach on-prem
networks behind the SD-WAN.

Verify BGP route advertisement:

```bash
aws ec2 get-transit-gateway-attachment-propagations \
  --transit-gateway-attachment-id <connect-attachment-id>
```

## Route table quota tuning

Default quotas (soft limits, raise via AWS Support):

| Resource | Default | Max |
|---|---|---|
| Route tables per TGW | 50 | 100 |
| Routes per route table | 10000 | 100000 |
| Propagations per route table | 100 | 100 |
| Associations per route table | 100 | 100 |

Plan route table fan-out for large topologies: with N attachments
and M route tables, worst case is N*M propagations. Use Cloud WAN
to manage route table fan-out via policy for topologies >5 TGWs.
