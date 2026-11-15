#!/usr/bin/env bash
# Run the code model of the compute-first solver (copilot/compute.py) as a third
# systemd service, on its own port. It does not touch math-llm or math-embed.
# It downloads the model if it is missing. Run it again whenever you change the
# COMPUTE_* keys in config.env.
source "$(dirname "$0")/common.sh"

[ -n "${COMPUTE_FILE:-}" ] || die "COMPUTE_FILE is not set. Add the COMPUTE_* keys to config.env first."
COMPUTE_PATH="$MODELS_DIR/$COMPUTE_FILE"
[ -x "$LLAMA_SERVER" ] || die "llama-server not found. Run ./board/02_build_llama_cpp.sh first."

step "$COMPUTE_FILE"
mkdir -p "$MODELS_DIR"
if [ ! -f "$COMPUTE_PATH" ]; then
  url="https://huggingface.co/$COMPUTE_REPO/resolve/$COMPUTE_REVISION/$COMPUTE_FILE"
  wget --quiet --show-progress --continue -O "$COMPUTE_PATH.part" "$url"
  mv "$COMPUTE_PATH.part" "$COMPUTE_PATH"
fi
if [ -n "${COMPUTE_SHA256:-}" ]; then
  echo "  verifying SHA256..."
  echo "$COMPUTE_SHA256  $COMPUTE_PATH" | sha256sum --check --status \
    || die "$COMPUTE_FILE doesn't match its SHA256. Delete it and run this script again."
fi
ok "model ready: $(du -h "$COMPUTE_PATH" | cut -f1)"

pid="$(pgrep -f -- "llama-server.*--port $COMPUTE_PORT" | head -1 || true)"
service_pid="$(systemctl show -p MainPID --value math-compute 2>/dev/null || true)"
if [ -n "$pid" ] && [ "$pid" != "$service_pid" ]; then
  die "a llama-server you started by hand (PID $pid) is using port $COMPUTE_PORT. Stop it with: kill $pid"
fi

step "Installing math-compute.service"
sed -e "s|@USER@|$USER|g" \
    -e "s|@LLAMA_SERVER@|$LLAMA_SERVER|g" \
    -e "s|@COMPUTE_PATH@|$COMPUTE_PATH|g" -e "s|@COMPUTE_PORT@|$COMPUTE_PORT|g" \
    -e "s|@COMPUTE_THREADS@|${COMPUTE_THREADS:-4}|g" -e "s|@COMPUTE_CTX@|${COMPUTE_CTX:-4096}|g" \
    -e "s|@COMPUTE_ALIAS@|${COMPUTE_ALIAS:-compute}|g" \
    "$REPO_DIR/board/systemd/math-compute.service" | sudo tee /etc/systemd/system/math-compute.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable math-compute
sudo systemctl restart math-compute

step "Installing math-compute-warm.service"
sed -e "s|@USER@|$USER|g" -e "s|@REPO_DIR@|$REPO_DIR|g" \
    "$REPO_DIR/board/systemd/math-compute-warm.service" | sudo tee /etc/systemd/system/math-compute-warm.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable math-compute-warm

step "Waiting for the server to load the model"
wait_for_health "$COMPUTE_PORT" 300 || die "the compute server didn't start. See: journalctl -u math-compute -n 50"
ok "compute server ready on 127.0.0.1:$COMPUTE_PORT"
sudo systemctl start --no-block math-compute-warm
ok "reading the examples into the server cache in the background (about 6 minutes the first time)"
echo "        Follow it: journalctl -u math-compute-warm -f"
free -m | awk 'NR==2 {printf "  RAM: %d MB used, %d MB available\n", $3, $7}'
ok "Next: python3 predict.py --input data/sample_problems.jsonl --output results/check.csv"
