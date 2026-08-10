# Baseline (no-skill) — dedicated-master-large-cluster

> This is the response a model produces **without** the skill
> definition. It creates a cluster but misses the dedicated master
> sizing rule (c6g.2xlarge for 12 data nodes), the UltraWarm / cold
> storage lifecycle, the manual snapshot repository registration
> flow, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to set up a large OpenSearch cluster for logs:

```bash
aws opensearch create-domain \
  --domain-name prod-logs \
  --engine-version OpenSearch_2.11 \
  --cluster-config \
    InstanceType=r6g.4xlarge.search,InstanceCount=12,\
ZoneAwarenessEnabled=true,ZoneAwarenessConfig={AvailabilityZoneCount=3} \
  --ebs-options EBSEnabled=true,VolumeType=gp3,VolumeSize=500
```

For warm and cold storage, you can add UltraWarm later via
update-domain-config. Manual snapshots can be configured after domain
creation.
