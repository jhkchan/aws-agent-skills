# Baseline (no-skill) response: cur2-split-cost-allocation-automated

This file captures what a generic assistant produces WITHOUT the
cur-automation-automator skill loaded — the contrast that proves the
skill emits the correct BCM Data Exports API (not the legacy `cur`
API) and verifies the Container Insights prerequisite.

---

To set up CUR 2.0 with split cost allocation for your EKS cluster:

1. In the Billing console, enable Split Cost Allocation Data:
   - Billing → Cost and Usage Reports → Split Cost Allocation Data → Enable
2. Wait 24-48 hours for SCAD data to populate.
3. Run a query to see per-pod cost:

```sql
SELECT resource_id, SUM(unblended_cost) AS cost
FROM cur_data
WHERE product_code = 'AmazonEKS'
  AND month = '08'
GROUP BY resource_id
ORDER BY cost DESC;
```

This should give you per-pod attribution. Note that you may need to
have CloudWatch Container Insights enabled on the cluster for the
split data to be accurate.

Let me know if you need help interpreting the SCAD columns.
