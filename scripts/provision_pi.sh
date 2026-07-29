#!/usr/bin/env bash
set -euo pipefail

llama_revision="f5b9bd39b56c7a7839a9795a100b6a00b84ac961"
llm_revision="7dabda4d13d513e3e842b20f0d435c732f172cbe"
llm_sha256="626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d"
embedding_revision="370f27d7550e0def9b39c1f16d3fbaa13aa67728"
embedding_sha256="06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
data_root="/var/lib/pi-local-rag"
format_device=""
confirm_device=""
disable_overlayfs=false

usage() {
  echo "Usage: $0 [--format-nvme DEVICE --confirm-format DEVICE] [--disable-overlayfs]"
  echo "Run from the repository root on a Raspberry Pi 5."
}

download_verified() {
  local url="$1"
  local output="$2"
  local checksum="$3"
  if [[ -f "$output" ]] && printf "%s  %s\n" "$checksum" "$output" | sha256sum -c - >/dev/null; then
    echo "Verified existing model: $output"
    return
  fi
  sudo -u rag curl -fL --retry 5 --continue-at - -o "$output" "$url"
  printf "%s  %s\n" "$checksum" "$output" | sha256sum -c -
}

while (($#)); do
  case "$1" in
    --format-nvme) format_device="${2:?missing device}"; shift 2 ;;
    --confirm-format) confirm_device="${2:?missing device}"; shift 2 ;;
    --disable-overlayfs) disable_overlayfs=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$(uname -m)" == "aarch64" ]] || {
  echo "This provisioner requires ARM64 Raspberry Pi OS/Debian." >&2
  exit 1
}
[[ -f pyproject.toml && -f deploy/systemd/rag-api.service ]] || {
  echo "Run this script from the repository root." >&2
  exit 1
}

if findmnt -n -o FSTYPE / | grep -qx overlay; then
  if [[ "$disable_overlayfs" != true ]]; then
    echo "Root uses volatile overlayfs. Re-run with --disable-overlayfs, then reboot." >&2
    exit 1
  fi
  sudo raspi-config nonint disable_overlayfs
  echo "Overlayfs disabled. Reboot, then run this script again without --disable-overlayfs."
  exit 20
fi

if [[ -n "$format_device" ]]; then
  [[ "$format_device" == /dev/nvme*n* && "$confirm_device" == "$format_device" ]] || {
    echo "NVMe formatting requires matching --confirm-format DEVICE." >&2
    exit 2
  }
  [[ -b "$format_device" ]] || { echo "Not a block device: $format_device" >&2; exit 1; }
  root_source="$(findmnt -n -o SOURCE /)"
  if [[ "$root_source" == "$format_device"* ]] ||
    lsblk -nrpo MOUNTPOINTS "$format_device" | grep -q '[^[:space:]]'; then
    echo "Refusing to format a mounted or root device: $format_device" >&2
    exit 1
  fi
  sudo wipefs --all "$format_device"
  sudo parted --script "$format_device" mklabel gpt mkpart primary ext4 1MiB 100%
  sudo partprobe "$format_device"
  partition="${format_device}p1"
  sudo mkfs.ext4 -F -L pi-rag-data "$partition"
  uuid="$(sudo blkid -s UUID -o value "$partition")"
  sudo install -d -m 0755 "$data_root"
  if ! grep -q "$uuid" /etc/fstab; then
    printf "UUID=%s %s ext4 defaults,noatime 0 2\n" "$uuid" "$data_root" |
      sudo tee -a /etc/fstab >/dev/null
  fi
  sudo mount "$data_root"
fi

findmnt -rn "$data_root" >/dev/null || {
  echo "$data_root must be a persistent mounted filesystem." >&2
  exit 1
}

sudo apt-get update
sudo apt-get install -y build-essential cmake curl git libopenblas-dev parted python3-venv rsync
getent passwd rag >/dev/null ||
  sudo useradd --system --home-dir "$data_root" --shell /usr/sbin/nologin rag
sudo chown rag:rag "$data_root"

llama_root="/opt/llama.cpp"
if [[ ! -d "$llama_root/.git" ]]; then
  sudo git clone --no-checkout https://github.com/ggml-org/llama.cpp "$llama_root"
fi
sudo git -C "$llama_root" fetch --depth 1 origin "$llama_revision"
sudo git -C "$llama_root" checkout --detach "$llama_revision"
sudo cmake -S "$llama_root" -B "$llama_root/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DLLAMA_CURL=OFF
sudo cmake --build "$llama_root/build" --target llama-server -j"$(nproc)"
sudo cp -a "$llama_root"/build/bin/lib*.so* /usr/local/lib/
sudo install -m 0755 "$llama_root/build/bin/llama-server" /usr/local/bin/llama-server
sudo ldconfig

llm_dir="$data_root/models/llm"
embedding_dir="$data_root/models/embedding"
sudo install -d -o rag -g rag "$llm_dir" "$embedding_dir"
llm_file="$llm_dir/qwen2.5-3b-instruct-q4_k_m.gguf"
embedding_file="$embedding_dir/Qwen3-Embedding-0.6B-Q8_0.gguf"
download_verified \
  "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/$llm_revision/qwen2.5-3b-instruct-q4_k_m.gguf" \
  "$llm_file" "$llm_sha256"
download_verified \
  "https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/$embedding_revision/Qwen3-Embedding-0.6B-Q8_0.gguf" \
  "$embedding_file" "$embedding_sha256"

scripts/install.sh
printf "%s\n" \
  "RAG_DATA_DIR=$data_root" \
  "RAG_DATABASE_PATH=$data_root/rag.db" \
  "RAG_LLM_BACKEND=llamacpp" \
  "RAG_LLAMACPP_URL=http://127.0.0.1:8080" \
  "RAG_MODEL_NAME=qwen2.5-3b-instruct" \
  "RAG_EMBEDDING_URL=http://127.0.0.1:8081" \
  "RAG_EMBEDDING_MODEL=qwen3-embedding-0.6b" \
  "RAG_ENABLE_KG=false" \
  "RAG_ENABLE_GRAPHRAG=false" \
  "RAG_ENABLE_VOICE=false" |
  sudo tee /etc/pi-local-rag.env >/dev/null
sudo chown root:rag /etc/pi-local-rag.env
sudo chmod 0640 /etc/pi-local-rag.env
sudo systemctl restart llama-server embedding-server rag-api rag-worker

curl -fsS --retry 30 --retry-delay 2 --retry-connrefused http://127.0.0.1:8080/health
curl -fsS --retry 30 --retry-delay 2 --retry-connrefused http://127.0.0.1:8081/health
curl -fsS --retry 30 --retry-delay 2 --retry-connrefused http://127.0.0.1:8000/health
echo
echo "Pi Local RAG is ready on http://$(hostname -I | awk '{print $1}'):8000"
