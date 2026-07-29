# Operations

Native systemd is the production default. Create a locked `rag` system account, clone into
`/opt/pi-local-rag`, run `scripts/install.sh`, then configure `/etc/pi-local-rag.env`.

Health: `curl -f http://127.0.0.1:8000/health`. Back up before updates with
`scripts/backup.sh`. Model files are managed separately and are never included in Git.
