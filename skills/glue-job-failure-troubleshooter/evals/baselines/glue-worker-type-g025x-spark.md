# Baseline (no-skill) response: glue-worker-type-g025x-spark

---

Your Glue Spark job is failing with memory errors after switching to
G.025X workers. G.025X workers are smaller than G.1X, so each executor
has less memory. The fix is to either increase the number of G.025X
workers or switch back to G.1X.

If you want to keep the cost savings of G.025X, try optimizing your
Spark script to use less memory per executor. You can also try
repartitioning the input data into smaller chunks.
