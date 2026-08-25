# Error Handling — sitewise-asset-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Error handling

### Asset model stuck in CREATING state
- The model is being validated. If it stays in CREATING for more than a
  minute, check for invalid transform/metric expressions or circular
  property references. A model in CREATING for several minutes likely
  has a validation error — check `describe-asset-model` for error
  details.

### Gateway shows ERROR state
- Check the Greengrass core device logs on the edge device. Common
  causes: OPC-UA server unreachable, certificate trust failure,
  insufficient Greengrass permissions, or the core device is offline.

### No data appears in dashboards despite ingestion
- Verify the asset property alias matches the alias used in the
  ingestion call (or the OPC-UA nodePathMapping). Check
  BatchPutAssetPropertyValue error entries. Confirm the property is a
  measurement (transforms/metrics derive from measurements, not from
  external data). Verify the asset status is ACTIVE.

### Portal dashboards show no data
- The portal IAM role lacks permissions to read asset data. Verify the
  role has `iotsitewise:BatchGetAssetPropertyAggregates`,
  `BatchGetAssetPropertyValue`, and `BatchGetAssetPropertyValueHistory`
  on the relevant assets. Also check that the access policy assigns
  the user/group to the correct project.

### Alarm never fires despite threshold breach
- The alarm duration (`durationInMinutes`) may be too long for the data
  frequency. If data arrives every 60 seconds but the duration is 10
  minutes, the alarm needs 10 minutes of sustained breach. Also verify
  the alarm references the correct property ID and comparison operator.

