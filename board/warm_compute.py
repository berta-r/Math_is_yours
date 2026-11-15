#!/usr/bin/env python3
"""Read the compute solver's examples into the llama-server cache, once, after boot.

Run by math-compute-warm.service (board/06_compute_server.sh installs it). The
first predict.py after a restart would otherwise spend about 6 minutes reading
the examples. Waits up to 10 minutes for math-compute to answer, then calls
copilot.compute.warm_up(force=True). Always exits 0, so systemd never retries it
in a loop: predict.py still falls back to the letter call if the server is down.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from copilot.client import get  # noqa: E402
from copilot.config import CONFIG  # noqa: E402

POLL_SECONDS = 2
WAIT_SECONDS = 600


def say(message):
    print(f"[warm_compute] {message}", file=sys.stderr, flush=True)


def main():
    port = CONFIG.get("COMPUTE_PORT") or CONFIG["LLM_PORT"]
    health = f"http://127.0.0.1:{port}/health"
    started = time.monotonic()
    while True:
        try:
            get(health, timeout=5)
            break
        except Exception as error:  # not up yet, or still loading the model (503)
            if time.monotonic() - started >= WAIT_SECONDS:
                say(f"no answer from {health} after {WAIT_SECONDS} s ({error}); nothing warmed")
                return 0
            time.sleep(POLL_SECONDS)
    say(f"server on port {port} is up after {time.monotonic() - started:.0f} s; reading the examples...")
    try:
        from copilot import compute
        ready = compute.warm_up(force=True)
    except Exception as error:  # never fail the unit
        say(f"warm-up failed ({type(error).__name__}: {error})")
        return 0
    say(f"done in {time.monotonic() - started:.0f} s: " + ("examples cached" if ready else "server not usable"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
