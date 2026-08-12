# Baseline (no-skill) response: glue-dpu-insufficient-g1x-oom

---

Your Glue job is failing with a YARN memory error. The "Container
killed by YARN" message means the executor ran out of memory. Since
the dataset grew 5x, you probably need to fix a memory issue in your
Spark script — look for any operations that load large amounts of data
into memory at once, like collect() or broad joins.

You could also try increasing the number of workers to give each
executor less data to process. Or add more memory by using a larger
worker type.
