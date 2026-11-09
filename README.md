# EcoRoute

EcoRoute is a local-first prototype for routing a batch of prompts. A keyword and length filter sends potentially complex prompts to the heavier configured Fireworks model. Other prompts go to a local Ollama model first. A local escalation signal or failed response routes the original prompt to the cheaper configured Fireworks model.

## Run a batch

Build the image and run these commands from a POSIX shell in the repository root. Set FIREWORKS_API_KEY in your environment before running a batch that may use the cloud. Set ALLOWED_MODELS to a comma-separated list of model IDs available to your Fireworks account if you need to override the defaults in config.py. The first model is used for the cheaper route and the last for the heavier route.

```sh
docker build -t ecoroute-agent .
docker run --rm -e FIREWORKS_API_KEY -e ALLOWED_MODELS \
  -v "$PWD/input:/input:ro" -v "$PWD/output:/output" ecoroute-agent
python benchmark.py output/results.json
```

The runner reads input/tasks.json and writes output/results.json. Cloud routes transmit the original prompt to the configured provider. The local stage uses Qwen2.5:1.5B by default and considers up to 2,000 characters per prompt.

## Read the benchmark

The checked-in sample records six successful local results and four successful cloud results. The benchmark counts the recorded routes, separates errors, and reports the local share of all results. The sample does not measure answer quality, latency, token usage, or cost. Measuring savings would require a cloud-only baseline on the same prompts and observed usage for both runs.

## Compare routing with a cloud-only baseline

Set FIREWORKS_API_KEY and use the same input and cloud model configuration in both runs. The baseline uses the configured heavier model for every nonempty prompt.

```sh
docker run --rm -e FIREWORKS_API_KEY -e ALLOWED_MODELS \
  -v "$PWD/input:/input:ro" -v "$PWD/output:/output" \
  ecoroute-agent --mode routed --output /output/routed.json
docker run --rm -e FIREWORKS_API_KEY -e ALLOWED_MODELS \
  -v "$PWD/input:/input:ro" -v "$PWD/output:/output" \
  ecoroute-agent --mode cloud-only --output /output/cloud-only.json
python benchmark.py output/routed.json --baseline output/cloud-only.json
```

The comparison checks that task IDs and prompt hashes match. It reports route counts, failures, median and p95 processing latency, and observed cloud input and output tokens for each run. Processing latency includes inference and retries after a task acquires its concurrency slot. It excludes queue time and startup. Token totals cover reported usage from final cloud responses. Usage missing from those responses or incurred by failed retry attempts can be absent from the totals. Compare answer quality separately with a fixed scoring rubric before drawing conclusions about the routing trade-off.

The batch runner validates inputs before inference and rejects duplicate task IDs. Results retain input order and replace the previous output only after the full batch finishes.
