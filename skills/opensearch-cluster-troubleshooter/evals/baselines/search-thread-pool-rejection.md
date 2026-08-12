# Baseline (no-skill) response: search-thread-pool-rejection

---

Your OpenSearch cluster is rejecting search requests with 429. The
search thread pool queue is full. You can try increasing the search
queue size via the cluster settings, or scale out the cluster to
handle more concurrent searches.

If there's a particular slow query driving the rejections, you
might want to optimise that query.
