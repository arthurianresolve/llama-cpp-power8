# Recorded environment

- Captured: 2026-09-21 04:30-04:31 UTC.
- Host: Windows 11 Pro 10.0.26100, 64-bit.
- CPU: Intel Core i7-10610U at 1.80 GHz; 4 physical cores and 8 logical
  processors on the host.
- Host power: Balanced plan, AC connected, battery at 95% at capture.
- Runtime: WSL2, Ubuntu 24.04.4 LTS, Linux
  6.18.33.2-microsoft-standard-WSL2, x86-64.
- WSL allocation: 6 logical CPUs, 9.7 GiB RAM, 4.0 GiB swap.
- Measurement affinity: 4 threads, CPUs 0-3, strict CPU mask `f`; two WSL CPUs
  left free.
- Backend: CPU only, Haswell dispatch library; no accelerator device reported.
- Initial load average: 0.64, 0.86, 0.43.
- Final load average: 2.02, 1.21, 0.58.
- Warm-up: one complete invocation, discarded.
- Measured sampling: seven serialized invocations, 10 repetitions per workload
  per invocation, two seconds between invocations.

The host was not a bare-metal Linux installation and CPU frequency was not
fixed. Those limits are reflected in the reported spread and prohibit treating
the result as a cross-machine or POWER8 comparison.
