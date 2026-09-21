# Controlled x86-64 `pp128`/`tg32` reference run

This run demonstrates the evidence required for a reproducible `llama-bench`
result: immutable tool and model identities, an exact command, host and thread
configuration, repeated raw samples, and variability. It does not measure
POWER8 hardware and cannot validate or be compared with the historical POWER8
figures in the repository README.

The pull request was documentation-only, so there is no baseline/candidate
performance hypothesis. The measured values below are a descriptive x86-64
control for the two distinct workloads named in the README.

## Frozen identities

- Repository head when measured:
  `e4c06347c135d619a9bccb25970638583965b31e`.
- `llama.cpp` release: `b11065`, commit
  `ce8caa6e60a03093351d6016a818720e0d46f0fb`.
- Official Ubuntu x86-64 CPU asset:
  `llama-b11065-bin-ubuntu-x64.tar.gz`.
- Asset SHA-256:
  `f00971c1b044fae179230bfc6f8d9f8461b778fef9ffac2b450088081a8ecd43`.
- Model: [`ggml-org/SmolLM2-135M-GGUF`, Q4_K_M](https://huggingface.co/ggml-org/SmolLM2-135M-GGUF/blob/main/SmolLM2-135M-Q4_K_M.gguf),
  134,515,008 parameters.
- Model SHA-256:
  `e3131339bf4e8065265593d4fd8f7bb7ff2d3abff1edb5618aa1197b89cad9f5`.
- Command record SHA-256:
  `d887f5d9b1c1133f775243291e2a2279425178ca1c3bb6bba93572a86ed0da76`.

The binary reported `llama.cpp` 0.4.1-dev, build 11065, commit
`ce8caa6e6`, built with GCC 11.4.0 for Linux x86-64. It loaded the Haswell CPU
backend and reported no accelerator devices. See [environment.md](environment.md)
for the recorded host boundary.

## Method

The final measurement used four threads pinned to WSL CPUs 0-3, leaving two of
the six exposed WSL CPUs free. CPU affinity was strict, GPU layers were disabled,
and the Windows host remained on its Balanced power plan while connected to AC.

```text
OMP_NUM_THREADS=4 taskset -c 0-3 llama-bench \
  -m SmolLM2-135M-Q4_K_M.gguf \
  -t 4 -C f --cpu-strict 1 \
  -p 128 -n 32 -r 10 \
  -ngl 0 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa auto \
  --no-warmup -o jsonl
```

One complete invocation was discarded as warm-up. Seven measured invocations
then ran serially with a two-second delay. Each invocation retained 10 raw
samples for both `pp128` and `tg32`, giving 70 samples per workload. All seven
invocations exited zero. No samples were removed.

## Results

The primary statistic is the median of the seven per-invocation averages emitted
by `llama-bench`. The coefficient of variation (CV) describes those seven
averages. Raw-sample quartiles and full ranges expose scheduler stalls instead
of hiding them.

| Workload | Median run average | Run-average range | Run-average CV | Raw median | Raw IQR | Full raw range |
|----------|-------------------:|------------------:|---------------:|-----------:|--------:|---------------:|
| `pp128` | 435.42 tokens/s | 411.15-466.72 | 4.02% | 434.44 | 426.74-454.44 | 309.36-530.85 |
| `tg32` | 136.26 tokens/s | 128.02-145.67 | 4.55% | 138.50 | 131.90-144.28 | 65.51-153.88 |

The complete machine-readable summary is in [summary.json](summary.json), and
the seven original JSONL outputs plus exit/load record are under [raw](raw/).
The slow samples remain in those files and in every statistic above.

## Correctness and validity

- Every measured `llama-bench` process loaded the pinned model and completed
  both workloads with exit code 0.
- A separate deterministic `llama-cli` smoke run loaded the same model,
  generated eight tokens, and exited 0; its compact record is in
  [correctness.txt](correctness.txt).
- The measurement is valid as descriptive evidence for this exact model,
  binary, x86-64/WSL host, thread configuration, and workload.
- It is not evidence of POWER8 throughput, an x86-versus-POWER8 comparison, a
  speedup, or the methodology behind any historical table row.
- WSL scheduling and the host's Balanced power plan limit repeatability across
  machines. The full ranges are therefore material, even though the run-average
  CV stayed below 5% for both workloads.

Run [run.sh](run.sh) from this directory to download the pinned artifacts,
verify their hashes, and repeat the same sampling plan.

```sh
bash run.sh
# Or choose a cache location with enough space for the model and extracted tool:
WORKDIR=/path/to/benchmark-cache bash run.sh
```

The runner requires Linux x86-64, Bash, curl, tar, sha256sum, lscpu, and taskset,
with CPUs 0-3 available to the process. It rechecks the cached archive and model
on every invocation, then extracts the verified archive into a fresh
`WORKDIR/run.XXXXXXXX/bin` directory. Binaries or libraries from an earlier
extraction are never reused. Each invocation keeps its own `results` directory,
including a discarded warm-up, so reruns cannot overwrite earlier evidence.
The path is printed before measurement; failed runs retain their diagnostics.

The committed raw samples and statistics above remain the original reference
record. A rerun produces a separate observation, not a replacement measurement.
Setup regression tests use tiny synthetic fixtures and make no performance claim:

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
```
