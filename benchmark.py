import json
import os

OUTPUT_FILE = "output/results.json"
CLOUD_COST_PER_TASK = 0.005 # Estimated premium cloud cost

if not os.path.exists(OUTPUT_FILE):
    print("Run your Docker container first to generate results!")
    exit()

with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

local_count = sum(1 for r in results if not r["answer"].startswith("Error") and "Bubble Sort" not in r["answer"])
cloud_count = len(results) - local_count
total_saved = local_count * CLOUD_COST_PER_TASK

print("\n" + "="*40)
print(" 🚀 ECOROUTE BENCHMARK REPORT ")
print("="*40)
print(f"Total Tasks Processed: {len(results)}")
print(f"Handled Locally (Zero Cost): {local_count}")
print(f"Escalated to Cloud: {cloud_count}")
print(f"Local Intercept Rate: {(local_count/len(results))*100:.1f}%")
print("-" * 40)
print(f"💰 Total API Funds Saved: ${total_saved:.4f}")
print("="*40 + "\n")