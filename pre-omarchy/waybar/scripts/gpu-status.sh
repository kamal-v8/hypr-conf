#!/usr/bin/env bash
# Waybar custom module: NVIDIA dGPU (GTX 1650) usage
# Outputs JSON: text, tooltip, class, percentage

set +e

json_escape() {
  # Escape a string for embedding in JSON double quotes
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

emit() {
  local text=$1 tooltip=$2 class=$3 percentage=$4
  printf '{"text":"%s","tooltip":"%s","class":"%s","percentage":%s}\n' \
    "$(json_escape "$text")" \
    "$(json_escape "$tooltip")" \
    "$(json_escape "$class")" \
    "$percentage"
}

# Find NVIDIA GPU path dynamically
NVIDIA_GPU_PATH=""
for dev in /sys/bus/pci/devices/*; do
  if [ -f "$dev/vendor" ]; then
    if [ "$(cat "$dev/vendor")" = "0x10de" ]; then
      NVIDIA_GPU_PATH="$dev"
      break
    fi
  fi
done

# If NVIDIA GPU is suspended, output "Off" and exit to save battery & prevent lag
if [ -n "$NVIDIA_GPU_PATH" ] && [ -f "$NVIDIA_GPU_PATH/power/runtime_status" ]; then
  gpu_status=$(cat "$NVIDIA_GPU_PATH/power/runtime_status")
  if [ "$gpu_status" = "suspended" ]; then
    emit "Off" "NVIDIA GPU is suspended (low power mode)" "gpu-suspended" 0
    exit 0
  fi
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  emit "--" "nvidia-smi not found" "gpu-error" 0
  exit 0
fi

# Sample twice (~250ms apart) and take the max util — single samples often
# read 0% on bursty CUDA workloads (LLM inference, games loading, etc.).
read_gpu() {
  timeout 1.5 nvidia-smi \
    --query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,memory.reserved \
    --format=csv,noheader,nounits 2>/dev/null | head -n1
}

out1=$(read_gpu)
sleep 0.25
out2=$(read_gpu)

# Prefer the sample that has higher util; fall back to whichever exists
out=""
util1=0
util2=0
if [[ -n "$out1" ]]; then
  util1=$(printf '%s' "$out1" | awk -F',' '{gsub(/ /,"",$2); print $2+0}')
  out=$out1
fi
if [[ -n "$out2" ]]; then
  util2=$(printf '%s' "$out2" | awk -F',' '{gsub(/ /,"",$2); print $2+0}')
  if (( util2 >= util1 )); then
    out=$out2
  fi
fi

if [[ -z "$out" ]]; then
  emit "--" "dGPU unavailable (nvidia-smi failed)" "gpu-error" 0
  exit 0
fi

# Parse CSV: name, util, mem_util, mem_used, mem_total, temp, power, mem_reserved
IFS=',' read -r name util mem_util mem_used mem_total temp power mem_reserved <<<"$out"

trim() {
  local s=$1
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

name=$(trim "$name")
util=$(trim "$util")
mem_util=$(trim "$mem_util")
mem_used=$(trim "$mem_used")
mem_total=$(trim "$mem_total")
temp=$(trim "$temp")
power=$(trim "$power")
mem_reserved=$(trim "$mem_reserved")

[[ "$util" =~ ^[0-9]+([.][0-9]+)?$ ]] || util=0
[[ "$mem_util" =~ ^[0-9]+([.][0-9]+)?$ ]] || mem_util=0
[[ "$mem_used" =~ ^[0-9]+([.][0-9]+)?$ ]] || mem_used=0
[[ "$mem_total" =~ ^[0-9]+([.][0-9]+)?$ ]] || mem_total=0
[[ "$mem_reserved" =~ ^[0-9]+([.][0-9]+)?$ ]] || mem_reserved=0
[[ "$temp" =~ ^[0-9]+([.][0-9]+)?$ ]] || temp="?"
[[ "$power" =~ ^[0-9]+([.][0-9]+)?$ ]] || power="?"

# Integer values for display / class thresholds
util_i=${util%%.*}
mem_used_i=${mem_used%%.*}
mem_reserved_i=${mem_reserved%%.*}
mem_total_i=${mem_total%%.*}

# Total occupied VRAM = process allocations + driver reservations
mem_occupied_i=$(( mem_used_i + mem_reserved_i ))

if (( mem_total_i > 0 )); then
  mem_pct=$(( mem_occupied_i * 100 / mem_total_i ))
else
  mem_pct=0
fi

# Human VRAM (GiB, one decimal)
mem_occupied_gib=$(awk -v m="$mem_occupied_i" 'BEGIN { printf "%.1f", m/1024 }')
mem_total_gib=$(awk -v m="$mem_total_i" 'BEGIN { printf "%.1f", m/1024 }')

if (( util_i >= 80 || mem_pct >= 90 )); then
  class="gpu-high"
elif (( util_i >= 40 || mem_pct >= 60 )); then
  class="gpu-mid"
else
  class="gpu-idle"
fi

text="${util_i}% ${mem_occupied_gib}G"

tooltip="${name}
Core: ${util_i}%
VRAM: ${mem_occupied_i}/${mem_total_i} MiB (${mem_pct}%) · ${mem_occupied_gib}/${mem_total_gib} GiB
  ├ Processes: ${mem_used_i} MiB
  └ Reserved:  ${mem_reserved_i} MiB
Temp: ${temp}°C
Power: ${power} W"

emit "$text" "$tooltip" "$class" "$util_i"
