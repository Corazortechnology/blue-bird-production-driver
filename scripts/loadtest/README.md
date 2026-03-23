# Realistic load tests (not just `/health`)

## What “real time / everything” means

| Layer | What to test | Tool hint |
|-------|----------------|-----------|
| **Cheap** | `GET /health` | `k6 run scripts/k6-health-load.js` |
| **Medium** | `POST /api/monitor/frame` (JPEG + driver/session) | `k6 run scripts/loadtest/monitor-frame-load.js` |
| **Heavy** | `wss://…/stream` (binary frames, ML loop) | k6 WebSocket, Locust, or custom client |

**Throughput for `/health` does not predict `/stream` or `/api/monitor/frame`.** ML + OpenCV paths use much more CPU/RAM.

---

## 1) One-time: small JPEG for multipart tests

From repo root, **one** of these:

```bash
# Option A — small JPEG from httpbin (usually works)
curl -fsSL -o scripts/loadtest/frame.jpg "https://httpbin.org/image/jpeg"

# Option B — random photo (follows redirects)
curl -fsSL -L -o scripts/loadtest/frame.jpg "https://picsum.photos/320/240.jpg"

# Option C — no network: create with Python (needs Pillow: pip install pillow)
python3 -c "from PIL import Image; Image.new('RGB',(320,240),(90,90,90)).save('scripts/loadtest/frame.jpg','JPEG',quality=85)"
```

(Or copy **any** small `.jpg` to `scripts/loadtest/frame.jpg`.)

---

## 2) Monitor frames (REST, realistic CPU path)

**Ramp slowly** — start with low VUs; this hits your API + fusion + DB more than `/health`.

```bash
cd "/path/to/repo"
k6 run scripts/loadtest/monitor-frame-load.js
```

`frame.jpg` must live in **`scripts/loadtest/`** next to `monitor-frame-load.js` (k6 resolves `open()` from the script’s folder, not only your shell `cwd`).

Watch while it runs:

```bash
kubectl top pod -n default -l app=api-service
```

---

## 3) WebSocket `/stream` (heaviest)

The server **accepts binary JPEG bytes** on the WebSocket and runs the full realtime pipeline.

- Load-testing **many** concurrent WebSockets usually needs a **custom script** (Node/Python) or **Locust** + `websocket-client`, not a single `curl`.
- Start with **1–5** real clients (browsers or a small script), then increase.

Example URL:

`wss://api.corazor.com/stream?driver_id=test-driver`

---

## 4) How to read “max users”

1. Define **one scenario** (e.g. “each user sends 2 frames/sec to `/api/monitor/frame`”).
2. **Ramp VUs** until errors &gt; 1–5% or p95 latency exceeds your SLO.
3. That point is your **approximate capacity** for that scenario — not a universal “user count.”

---

## 5) Safety

- Run against **staging** if you have it; production tests can affect real users.
- **Don’t** point absurd RPS at prod without agreement.
