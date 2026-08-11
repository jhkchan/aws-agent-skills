# Provisioning CLI Commands

## FSx for Windows
```bash
aws fsx create-file-system \
  --file-system-type WINDOWS \
  --storage-capacity 1024 \
  --storage-type SSD \
  --windows-configuration DeploymentType=MULTI_AZ_1,\
ThroughputCapacity=128,\
ActiveDirectoryId=d-1234567890,\
PreferredSubnetId=subnet-aaa11122,\
SubnetIds=subnet-aaa11122,subnet-bbb22233 \
  --security-group-ids sg-fsx111 \
  --kms-key-id alias/aws/fsx
```

## FSx for Lustre
```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 2400 \
  --lustre-configuration DeploymentType=PERSISTENT_1,\
PerUnitStorageThroughput=200,\
DataCompressionType=LZ4 \
  --subnet-ids subnet-aaa11122 \
  --security-group-ids sg-lustre111
```

## S3 Link for Lustre
```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --lustre-configuration DeploymentType=SCRATCH_2,\
DataRepositoryType=FSx_LUSTRE,\
DataRepositoryConfiguration="{ImportPath=s3://my-bucket/data,\
ExportPath=s3://my-bucket/results}" \
  --subnet-ids subnet-aaa11122
```

## FSx for ONTAP
```bash
aws fsx create-file-system \
  --file-system-type ONTAP \
  --storage-capacity 1024 \
  --ontap-configuration DeploymentType=MULTI_AZ_1,\
PreferredSubnetId=subnet-aaa11122,\
ThroughputCapacity=128 \
  --subnet-ids subnet-aaa11122,subnet-bbb22233
```

## Backup Management
```bash
aws fsx create-backup --file-system-id fs-1234567890
aws fsx restore-from-backup --backup-id backup-1234567890
```

## Monitoring
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name fsx-disk-used \
  --metric-name DiskUsed \
  --namespace AWS/FSx \
  --dimensions Name=FileSystemId,Value=fs-1234567890 \
  --threshold 90 --comparison-operator GreaterThanThreshold
```

## NEVER Patterns
1. Never create Single-AZ for production Windows file shares without accepting 99.9% SLA
2. Never skip DNS alias configuration for failover readiness
3. Never set throughput below 8 MB/s for active workloads
4. Never forget to validate AD trust before self-managed AD join
5. Never use SCRATCH for data that needs persistence
