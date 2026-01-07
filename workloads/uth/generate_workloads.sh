python3 workloads/uth/generate_uth_workload.py \
  --start 2025-01-01 --end 2026-01-01 \
  --interval-seconds 300 \
  --nodes node07,node08,node09 \
  --seed 42 \
  --out workloads/uth/uth_workload_2025.jsonl

# Same but hourly
# python3 workloads/uth/generate_uth_workload.py \
#   --start 2025-01-01 --end 2026-01-01 \
#   --interval-seconds 3600 \
#   --nodes node07,node08,node09 \
#   --out workloads/uth/uth_workload_2025_hourly.jsonl
