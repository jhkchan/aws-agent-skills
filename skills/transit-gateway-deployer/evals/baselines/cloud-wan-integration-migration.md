# Baseline (no-skill) response: cloud-wan-integration-migration

This file captures what a generic assistant produces WITHOUT the
transit-gateway-deployer skill loaded — contrast proves the skill
adds structure around non-disruptive TGW-to-core-network attach,
segment policy mapping, and the route-table re-association cutover.

---

Here's a plan to migrate your two TGWs to Cloud WAN.

The migration will:
- Attach prod-tgw-us-east-1 to core-network-0abc
- Attach prod-tgw-eu-west-1 to core-network-0abc
- Apply the prod / non-prod segment policy to both TGWs
- Be non-disruptive — existing route tables remain in place

Steps:

1. Attach each TGW to the core network.
2. Verify Cloud WAN-managed route tables appear.
3. Re-associate attachments to Cloud WAN-managed route tables when ready.

Commands:

```
aws networkmanager create-attachment \
  --core-network-id core-network-0abc \
  --attachment-type TRANSIT_GATEWAY \
  --edge-location us-east-1 \
  --resource-arn <us-east-1-tgw-arn>
aws networkmanager create-attachment \
  --core-network-id core-network-0abc \
  --attachment-type TRANSIT_GATEWAY \
  --edge-location eu-west-1 \
  --resource-arn <eu-west-1-tgw-arn>
```

Cloud WAN will then manage the route tables based on the segment
policy. Let me know if you need help with the cutover.
