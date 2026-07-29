# Raspberry Pi 5 部署指南

本指南重建目前 `pi5-1` 的 native systemd 部署：Qwen2.5 3B generation、
Qwen3 0.6B multilingual embedding、SQLite/FTS5及NVMe持久儲存。

## 風險及前置條件

- 目標為 Raspberry Pi 5、ARM64 Debian/Raspberry Pi OS及最少16GB RAM。
- 建議主動散熱及1TB NVMe。
- `--format-nvme` 會清除指定磁碟全部資料，必須同時提供完全相同的
  `--confirm-format`；切勿猜測device name。
- 模型及database存放於 `/var/lib/pi-local-rag`，程式存放於
  `/opt/pi-local-rag`。
- llama.cpp及兩個官方模型均鎖定revision及SHA-256，script會拒絕checksum不符的下載。

## 1. 在開發機建立release

```bash
npm --prefix apps/web ci
npm --prefix apps/web run build
rsync -az --delete \
  --exclude .git --exclude .venv --exclude node_modules --exclude data \
  ./ pi@PI_IP:/tmp/pi-local-rag-release/
```

登入Pi並切換到release目錄：

```bash
ssh pi@PI_IP
cd /tmp/pi-local-rag-release
```

## 2. 如有overlayfs，先關閉

檢查：

```bash
findmnt -n -o FSTYPE /
```

如果輸出為 `overlay`：

```bash
sudo scripts/provision_pi.sh --disable-overlayfs
sudo reboot
```

重啟後重新同步release，確認root filesystem為 `ext4`及`rw`。

## 3. 首次設定空白NVMe並部署

先以 `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL` 核對裝置。以下只係例子：

```bash
sudo scripts/provision_pi.sh \
  --format-nvme /dev/nvme0n1 \
  --confirm-format /dev/nvme0n1
```

script會：

1. 建立GPT及單一ext4 partition；
2. 以UUID加入 `/etc/fstab`並掛載；
3. 建立受限 `rag` system account；
4. 編譯鎖定版本的 llama.cpp ARM64/OpenBLAS server；
5. 下載並驗證generation及embedding模型；
6. 安裝FastAPI app及四個systemd services；
7. 執行三個health checks。

已存在並已掛載的NVMe不應再次格式化。更新部署時直接執行：

```bash
sudo scripts/provision_pi.sh
```

## 4. 驗證

```bash
systemctl is-active llama-server embedding-server rag-api rag-worker
curl -f http://127.0.0.1:8080/health
curl -f http://127.0.0.1:8081/health
curl -f http://127.0.0.1:8000/health
findmnt /var/lib/pi-local-rag
vcgencmd get_throttled
vcgencmd measure_temp
```

瀏覽器開啟 `http://PI_IP:8000`。Generation及embedding ports只綁定localhost，
LAN只暴露RAG API/Web UI的port 8000。

## 5. 維護

- 更新前：`sudo scripts/backup.sh /path/to/backup.tar.gz`
- 更新：重新建立及同步release，然後執行 `sudo scripts/provision_pi.sh`
- Logs：`journalctl -u llama-server -u embedding-server -u rag-api -u rag-worker`
- 模型目錄：`/var/lib/pi-local-rag/models`
- Database：`/var/lib/pi-local-rag/rag.db`

Voice預設關閉；Whisper及Piper模型不包含在這個核心RAG provisioner。
