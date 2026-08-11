# Baseline (without skill): invalid-allocation-strategy-spot

The model proceeds to create the compute environment without flagging the error:

1. Does NOT catch that BEST_FIT allocation strategy does not support Spot instances
2. Does not recommend SPOT_CAPACITY_OPTIMIZED for spot workloads
3. Does not mention the spot fleet role requirement
4. Attempts to create with invalid configuration
5. No validation of allocation strategy against instance type selection
