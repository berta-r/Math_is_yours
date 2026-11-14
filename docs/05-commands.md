# 05 · Commands

> A quick reference. Each command says **where** it runs. The full explanation with expected output for each step is in [../README.md](../README.md#the-steps-at-a-glance). Replace `<ip>` with the board's IP address.

Board repository path: `~/datathon-UPC-maths-qualcomm-arduino-unoq`. User: `arduino`.

## Connect (laptop)

```bash
ssh arduino@<ip>                          # normal
adb shell                                 # USB fallback (also needed when Wi-Fi is off)
ssh -L 8000:127.0.0.1:8000 arduino@<ip>   # forward the explorer or web page port
adb forward tcp:8000 tcp:8000             # same over USB
```

## Board setup (board, once): README steps 1–8

```bash
git clone <this repo> ~/datathon-UPC-maths-qualcomm-arduino-unoq && cd $_
bash board/00_check_board.sh        # read-only health check: RAM, disk, clock, internet
bash board/01_install_packages.sh   # apt: build-essential cmake git … (sudo, internet)
bash board/02_build_llama_cpp.sh    # build llama.cpp at the pinned commit (~30 min)
bash board/03_download_models.sh    # download the GGUF files and check SHA256 (resumable)
bash board/04_install_services.sh   # systemd math-llm (:8081) + math-embed (:8082)
bash board/05_smoke_test.sh         # end to end: both servers, an embedding, 5 sample problems
```

The README does steps 2–7 **by hand** so you learn what each one does. The scripts do the same thing.

## Data (laptop, then copy to the board)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r laptop/requirements.txt
python3 laptop/prepare_m3kang.py                          # eng,cat → data/train.jsonl, data/val.jsonl
python3 laptop/prepare_m3kang.py --languages eng --save-images   # + data/images/*.png
scp data/train.jsonl data/val.jsonl arduino@<ip>:~/datathon-UPC-maths-qualcomm-arduino-unoq/data/
scp -r data/images arduino@<ip>:~/datathon-UPC-maths-qualcomm-arduino-unoq/data/
```

## Run and measure (board)

```bash
# Contract check after any change: 5 rows, a letter each
python3 predict.py --input data/sample_problems.jsonl --output results/check.csv

# Official-style run
python3 predict.py --input data/val.jsonl --output results/predictions.csv [--rag 1]

# Evaluation (same 50-problem sample every time)
python3 eval.py --limit 50 --name baseline
python3 eval.py --limit 50 --rag 1 --name rag1
python3 eval.py --languages cat --limit 100 --name cat-baseline
python3 eval.py --limit 0 --name final      # whole validation set (~45 min for 281)
cat results/ablations.csv

# Retrieval index
python3 build_index.py --input data/train.jsonl --db data/index.db --only-with-options

# Explorer (open http://127.0.0.1:8000 after forwarding the port)
python3 explorer/server.py --host 0.0.0.0
```

## Services and health (board)

```bash
systemctl status math-llm math-embed
sudo systemctl restart math-llm math-embed
journalctl -u math-llm -n 50
curl -s 127.0.0.1:8081/health ; curl -s 127.0.0.1:8082/health
free -m                                  # RAM: App Lab + servers share about 3.6 GB
pgrep -a llama-server                    # who is holding a port?
```

## Common problems

| Symptom | Fix |
| --- | --- |
| `Connection refused` on 8081/8082 | The service is down: `systemctl status math-llm`, `journalctl -u math-llm` |
| `couldn't bind … port 8081` | Another llama-server is running: `pgrep -a llama-server`, then `pkill llama-server` or stop the service |
| llama-server disappears, `journalctl -k` shows OOM | Keep `--parallel 1 --cache-ram 0` and stop any servers you started by hand |
| `predict.py` answers D with `timeout` | The prompt is too long: use fewer RAG examples or a shorter prompt |
| SSH refused on port 22 | Empty host keys, see [README step 0.3](../README.md#03-connect-over-ssh) |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | `ssh-keygen -R <ip>` |
| apt or download certificate errors | The clock is wrong: `timedatectl` |
| SSH drops with Wi-Fi off | Expected. Use `adb shell` |

The full table is in [../README.md#troubleshooting](../README.md#troubleshooting).

## Student teaching app (PC or board Linux)

```bash
python3 student_app/server.py                # http://127.0.0.1:7011
python3 student_app/server.py --local-tutor  # optional loopback SLM hint selection
python3 -m unittest discover -s student_app -v
python3 laptop/eval_teaching.py              # synthetic logic comparison only
```

Use `python` on Windows. For the board app over Wi-Fi, run on the **PC**:

```powershell
ssh -o ExitOnForwardFailure=yes -N -L 127.0.0.1:7012:127.0.0.1:7011 arduino@BOARD_IP
```

Add `-i PATH_TO_PRIVATE_KEY` when using a dedicated key. Keep the command running
and open **http://127.0.0.1:7012**. The laptop prototype can keep using port 7011.
Wi-Fi and USB app/model testing passed on the UNO Q. USB reconnect reopens the
page while the temporary watcher runs; Windows login startup remains untested. Use [deployment instructions](../board/STUDENT_DEPLOYMENT.md)
for the boot service and USB helper, [student app instructions](../student_app/README.md)
for practice, and [annotation workflow](../knowledge/README.md) for preparation.

For the temporary USB test on this already prepared **PC**, without installing
anything or changing startup settings:

```powershell
python laptop/usb_launcher.py watch --serial 2727288917 --port 7013
```

Use that serial only for the tested board; run `devices` to identify another one.
Open **http://127.0.0.1:7013** when ready. Keep the watcher running, and use Ctrl+C
to stop it if you started it in your own terminal. It does not restart after a PC
reboot. The Arduino boot service is independent and starts with the board.
