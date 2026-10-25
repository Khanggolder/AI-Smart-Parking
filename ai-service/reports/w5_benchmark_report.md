# W5 local engine and HTTP benchmark

## Setup and method

One real UFPR04 validation snapshot, 1280×720 JPEG, has **37 distinct polygons**. Cases 1, 10 and 37 use distinct polygons. Cases 50 and 100 repeat those polygons with unique benchmark spot IDs and are explicitly **synthetic workload**, not 50/100 independently configured real spaces. No ground-truth labels were provided to the inference engine.

Device: Intel64 Family 6 Model 154 Stepping 3 CPU and NVIDIA GeForce RTX 3050 Laptop GPU. Python 3.11, PyTorch 2.11.0+cu128, torchvision 0.26.0+cu128, batch size 32. GPU and CPU runs were performed sequentially. For **each device and each spot count**, there were 5 warm-up requests and 50 measured requests, separately for the in-process engine and actual localhost Uvicorn HTTP multipart endpoint. CUDA inference synchronizes when transferring outputs to CPU and at the engine timing boundary. Client wall latency uses a persistent HTTP connection; it includes request serialization, localhost transport, server processing and response parsing up to receipt of the HTTP response. It excludes frontend/backend, remote network, database and camera capture. Engine preprocessing includes image decode, validation, W1 polygon crop and tensor transforms. `model` includes batched forward/softmax/CPU transfer. Component p50 values need not add to total p50.

## Latency (milliseconds)

| Device | Spots | Workload | Pre p50 | Model p50 | Engine p50 / p95 | HTTP wall p50 / p95 |
|---|---:|---|---:|---:|---:|---:|
| CUDA | 1 | distinct | 7.0 | 5.5 | 12.8 / 18.0 | 19.0 / 24.7 |
| CUDA | 10 | distinct | 14.4 | 7.6 | 22.6 / 30.2 | 33.0 / 39.9 |
| CUDA | 37 | distinct | 34.9 | 24.5 | 62.5 / 75.2 | 74.5 / 109.0 |
| CUDA | 50 | synthetic workload | 49.9 | 30.3 | 83.5 / 94.8 | 104.2 / 117.7 |
| CUDA | 100 | synthetic workload | 102.3 | 75.1 | 182.3 / 223.9 | 194.8 / 252.8 |
| CPU | 1 | distinct | 8.6 | 9.1 | 17.1 / 18.8 | 19.1 / 23.1 |
| CPU | 10 | distinct | 18.3 | 21.4 | 40.0 / 42.7 | 40.9 / 50.2 |
| CPU | 37 | distinct | 44.3 | 75.1 | 120.8 / 130.3 | 125.9 / 148.3 |
| CPU | 50 | synthetic workload | 57.3 | 94.1 | 152.2 / 161.0 | 156.3 / 185.5 |
| CPU | 100 | synthetic workload | 105.2 | 194.7 | 303.8 / 330.9 | 324.5 / 356.2 |

GPU peak allocated memory, per warmed engine case: 18.4 MB (1 spot), 41.8 MB (10), 100.2 MB (37/50/100). This is PyTorch allocated memory, not total GPU usage. ModelLoader construction separately took 1467.4 ms on CUDA and 108.2 ms on CPU during these runs; process launch to `/ready` took 4351.1 ms and 4922.5 ms respectively. These are single startup observations, not p50, and are excluded from request latency.

## Concurrent local HTTP requests

Twenty requests for the **37 real polygons** were sent with 1, 2 or 4 client threads, using one Uvicorn process. Figures are client wall latency p95 and achieved throughput for those 20 requests:

| Device | Threads | p95 ms | Requests/s |
|---|---:|---:|---:|
| CUDA | 1 | 150.3 | 10.3 |
| CUDA | 2 | 156.5 | 13.8 |
| CUDA | 4 | 434.3 | 13.3 |
| CPU | 1 | 138.5 | 7.9 |
| CPU | 2 | 276.7 | 8.7 |
| CPU | 4 | 625.4 | 7.6 |

Concurrency adds queueing and resource contention; this short localhost trial is descriptive, not a capacity guarantee.

## NFR-02 interpretation

The measured 1280×720 snapshot with **37 distinct spots** has HTTP p95 109.0 ms on CUDA and 148.3 ms on CPU, below the 15-second SRS target on this local machine. The 100-spot results are for repeated polygons. **NFR-02 for 100 distinct real spots: NOT EVALUATED.** The 100-spot synthetic workload is below 15 seconds in this measurement but cannot certify the intended deployment, especially under concurrent or remote backend load.

Raw reproducible measurements: `runs/mobilenetv3_gpu/w5_evaluation/benchmark_cuda.json` and `benchmark_cpu.json` (Git ignored). Command: `python ai-service/scripts/benchmark_e2e.py --device cuda --runs 50 --warmup 5`; repeat with `--device cpu`. The script launches and stops its own Uvicorn process.
