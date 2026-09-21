#!/usr/bin/env bash
set -euo pipefail

asset=llama-b11065-bin-ubuntu-x64.tar.gz
asset_url="https://github.com/ggml-org/llama.cpp/releases/download/b11065/$asset"
asset_sha=f00971c1b044fae179230bfc6f8d9f8461b778fef9ffac2b450088081a8ecd43
model=SmolLM2-135M-Q4_K_M.gguf
model_url="https://huggingface.co/ggml-org/SmolLM2-135M-GGUF/resolve/main/$model"
model_sha=e3131339bf4e8065265593d4fd8f7bb7ff2d3abff1edb5618aa1197b89cad9f5

workdir=${WORKDIR:-"$PWD/.bench-work"}
downloads="$workdir/downloads"
bindir="$workdir/bin"
modeldir="$workdir/model"
results="$workdir/results"
mkdir -p "$downloads" "$bindir" "$modeldir" "$results"

fetch() {
    local url=$1
    local output=$2
    if [[ ! -f $output ]]; then
        curl -fL --retry 3 --output "$output" "$url"
    fi
}

fetch "$asset_url" "$downloads/$asset"
printf '%s  %s\n' "$asset_sha" "$downloads/$asset" | sha256sum --check -

if [[ ! -x $bindir/llama-b11065/llama-bench ]]; then
    tar -xzf "$downloads/$asset" -C "$bindir"
fi

fetch "$model_url" "$modeldir/$model"
printf '%s  %s\n' "$model_sha" "$modeldir/$model" | sha256sum --check -

bench="$bindir/llama-b11065/llama-bench"
export LD_LIBRARY_PATH="$bindir/llama-b11065"
export OMP_NUM_THREADS=4
export LC_ALL=C
export TZ=UTC

{
    date -u +%Y-%m-%dT%H:%M:%SZ
    uname -srmo
    lscpu
    free -h
} > "$results/environment.txt"
"$bench" --version > "$results/version.txt" 2>&1
"$bench" --list-devices > "$results/devices.txt" 2>&1

args=(
    -m "$modeldir/$model"
    -t 4 -C f --cpu-strict 1
    -p 128 -n 32 -r 10
    -ngl 0 -b 2048 -ub 512
    -ctk f16 -ctv f16 -fa auto
    --no-warmup -o jsonl
)

printf 'run\tstart_utc\texit\tload_average\n' > "$results/run-status.tsv"

run_one() {
    local name=$1
    local start load code
    start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    load=$(cut -d ' ' -f1-3 /proc/loadavg)
    set +e
    taskset -c 0-3 "$bench" "${args[@]}" \
        > "$results/$name.jsonl" 2> "$results/$name.stderr"
    code=$?
    set -e
    printf '%s\t%s\t%s\t%s\n' "$name" "$start" "$code" "$load" \
        >> "$results/run-status.tsv"
    return "$code"
}

run_one warmup
for run in 01 02 03 04 05 06 07; do
    sleep 2
    run_one "run-$run"
done

(
    cd "$results"
    sha256sum environment.txt version.txt devices.txt run-status.tsv \
        run-*.jsonl run-*.stderr > checksums.sha256
)

printf 'Results written to %s\n' "$results"
