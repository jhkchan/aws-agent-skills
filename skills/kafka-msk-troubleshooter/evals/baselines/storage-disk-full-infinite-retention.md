# Baseline (no-skill) response: storage-disk-full-infinite-retention

This file captures what a generic assistant produces WITHOUT the
kafka-msk-troubleshooter skill loaded.

---

Your Kafka brokers are running out of disk space. The disks are at 95%
full. You need to either increase the storage size or clean up old data.

To fix this, you can increase the EBS volume size for your brokers, or
set up retention policies to automatically delete old messages. You
should also check if there are any topics consuming excessive storage.

Consider deleting old topics or reducing the retention period to free
up disk space.
