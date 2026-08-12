# Baseline (no-skill) response: wlm-queue-timeout

---

Your query was cancelled due to a queue timeout. This means it was
waiting too long in the workload management queue. You can try
increasing the timeout setting or reducing the number of concurrent
queries.

Some options:
- Increase the WLM query timeout for the batch queue
- Run the query at a less busy time
- Optimize the query so it runs faster
- Add more slots to the queue

If this happens frequently, you may need to restructure your ETL
pipeline to submit fewer concurrent queries.
