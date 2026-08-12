# Baseline (no-skill) response: dlq-type-mismatch-fifo

---

Your StartMessageMoveTask failed because the source queue and DLQ have
different types. Your source queue is FIFO but your DLQ is standard.
You need to create a FIFO DLQ and update the RedrivePolicy on the
source queue to point to the new FIFO DLQ. Then you can redrive the
messages.

Make sure the new DLQ has a .fifo suffix and FifoQueue set to true.
